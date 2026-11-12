import time
import geopandas as gpd
import topojson as tp
import matplotlib.pyplot as plt
import os
import json
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from matplotlib.patches import Patch
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter
)
from django.core.management import call_command
from django.http import HttpResponse
from django_q.tasks import async_task
from django.db import IntegrityError, transaction
from django.utils import timezone
from jsmin import jsmin
from math import ceil
from api.v1.v1_publication.serializers import (
    ReviewListSerializer,
    ReviewSerializer,
    PublicationSerializer,
    PublicationInfoSerializer,
    CreatePublicationSerializer,
    PublicationReviewsSerializer,
    ReviewInfoSerializer,
    ExportMapSerializer,
    PublishedMapSerializer,
    CompareMapSerializer,
    RasterFilterSerializer,
    RasterListSerializer,
    RasterPushSerializer,
    RasterPushResponseSerializer,
)
from api.v1.v1_publication.models import (
    Review,
    Publication,
    Raster,
)
from api.v1.v1_publication.constants import (
    PublicationStatus,
    DroughtCategory,
    ExportMapTypes,
    DroughtCategoryColor,
    CDIGeonodeCategory,
)
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
from utils.custom_permissions import IsReviewer, IsAdmin, HasApiKey
from utils.modules import module_enabled
from utils.custom_pagination import Pagination
from utils.default_serializers import (
    DefaultResponseSerializer,
    CommonOptionSerializer,
)
from utils.custom_serializer_fields import validate_serializers_message


@extend_schema(
    description="Get required configuration",
    tags=["Development"],
    responses={200: {"type": "string", "format": "binary"}},
)
@api_view(["GET"])
def get_config_file(request, version):
    if not Path("source/config/config.min.js").exists():
        call_command("generate_config")
    data = jsmin(open("source/config/config.min.js", "r").read())
    response = HttpResponse(
        data, content_type="application/x-javascript; charset=utf-8"
    )
    return response


@extend_schema(
    responses={200: ReviewSerializer},
    tags=["Reviewer"],
    description="Manage publication reviews",
)
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsReviewer]
    pagination_class = Pagination

    def get_queryset(self):
        user = self.request.user
        return Review.objects.filter(
            user_id=user.id
        ).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        """
        Override the list method to add extra context.
        """
        queryset = self.get_queryset()

        # Paginate the queryset
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page,
            many=True,
        )
        return self.get_paginated_response(serializer.data)

    def get_serializer_class(self):
        """
        Use different serializers for list and detail views.
        """
        if self.action == 'list':
            return ReviewListSerializer
        return ReviewSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return super().get_serializer(*args, **kwargs)

    def perform_update(self, serializer):
        review_id = self.kwargs.get('pk')
        is_completed = Review.objects.get(id=review_id).is_completed

        instance = serializer.save()
        publication = instance.publication
        if not is_completed and instance.is_completed:
            job = Jobs.objects.create(
                type=JobTypes.review_completed,
                status=JobStatus.on_progress,
                result=ReviewSerializer(instance).data,
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_review_completed",
                instance.user.name,
                publication.year_month.strftime("%Y-%m"),
                publication.id,
                instance.id,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()
        # If all reviews are completed, update the publication status
        if (
            publication.reviews.filter(is_completed=False).count() == 0 and
            publication.status == PublicationStatus.in_review
        ):
            publication.status = PublicationStatus.in_validation
            publication.save()

    def perform_create(self, serializer):
        if not self.request.data.get("publication_id"):
            raise ValidationError({
                "publication_id": "This field is required."
            })
        serializer.save(
            user_id=self.request.user.id,
            publication_id=self.request.data["publication_id"],
        )


@extend_schema(
    responses={200: PublicationSerializer},
    tags=["Admin"],
    description="Manage publication process",
)
class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = Pagination

    def get_queryset(self):
        return Publication.objects.all().order_by("-due_date")

    def get_serializer_class(self):
        if self.action == "list":
            return PublicationInfoSerializer
        if self.action == 'create':
            return CreatePublicationSerializer
        return PublicationSerializer

    def perform_create(self, serializer):
        # Start a database transaction
        try:
            with transaction.atomic():
                # Exclude some fields from the data
                reviewers = serializer.validated_data.pop("reviewers", [])
                subject = serializer.validated_data.pop("subject")
                message = serializer.validated_data.pop("message")
                download_url = serializer.validated_data.pop(
                    "download_url", None
                )

                # Save the publication
                publication = serializer.save()

                # Link the source raster asset. The relation lives on Raster
                # (not on any GeoNode id); we still resolve it from the
                # transitional cdi_geonode_id the create flow passes.
                raster = None
                if publication.cdi_geonode_id:
                    raster = Raster.objects.filter(
                        geonode_id=publication.cdi_geonode_id
                    ).first()
                    if raster and publication.raster_id != raster.pk:
                        publication.raster = raster
                        publication.save(update_fields=["raster"])

                publication.reviews.set([
                    Review(publication=publication, user=reviewer)
                    for reviewer in reviewers
                ], bulk=False)

                if raster and raster.values:
                    # Platform path: the pipeline already reduced the raster to
                    # per-administration values and pushed them, so use them
                    # directly — no raster download / zonal stats needed.
                    from api.v1.v1_jobs.job import notify_reviewers
                    publication.initial_values = raster.values
                    publication.save(update_fields=["initial_values"])
                    notify_reviewers(publication, subject, message)
                elif publication.cdi_geonode_id and download_url:
                    # GeoNode fallback: download the raster, recompute
                    # initial_values via zonal stats, then notify reviewers.
                    timestamp = int(time.time())
                    filename = "raster_{0}_{1}.tif".format(
                        publication.cdi_geonode_id,
                        timestamp
                    )
                    job = Jobs.objects.create(
                        type=JobTypes.download_geonode_dataset,
                        status=JobStatus.on_progress,
                        info={
                            "publication_id": publication.id,
                            "filename": filename,
                            "subject": subject,
                            "message": message,
                        },
                    )
                    hook = "download_geonode_dataset_results"
                    task_id = async_task(
                        "api.v1.v1_jobs.job.download_geonode_dataset",
                        download_url,
                        filename,
                        hook=f"api.v1.v1_jobs.job.{hook}",
                    )
                    # Update the job with the task ID
                    job.task_id = task_id
                    job.save()
                else:
                    # geonode-less: trust the initial_values supplied in the
                    # request (no raster to fetch), notify reviewers directly.
                    from api.v1.v1_jobs.job import notify_reviewers
                    notify_reviewers(publication, subject, message)

                # Return the serialized publication data
                return PublicationSerializer(publication).data
        except IntegrityError as e:
            # Raise an appropriate exception if needed
            raise serializers.ValidationError({"messsage": f"{e}"})

    def perform_destroy(self, instance):
        instance.delete(hard=True)

    def perform_update(self, serializer):
        instance = serializer.save()
        total_adms = len(instance.initial_values)
        total_validated = 0
        if instance.validated_values:
            total_validated = len(list(filter(
                lambda x: x.get("category") or x.get("category") == 0,
                instance.validated_values
            )))
        instance.updated_at = timezone.now()
        if instance.narrative and total_adms == total_validated:
            instance.published_at = timezone.now()
        instance.save()


class PublicationReviewsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch publication reviews",
        description="Fetch reviews for a specific publication",
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="non_disputed",
                required=False,
                default=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="non_validated",
                required=False,
                default=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: PublicationReviewsSerializer,
            400: DefaultResponseSerializer,
            500: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)

        non_disputed = request.GET.get("non_disputed") in ["true", "1"]
        non_validated = request.GET.get("non_validated") in ["true", "1"]

        return Response(
            PublicationReviewsSerializer(
                instance=publication,
                context={
                    "non_disputed": non_disputed,
                    "non_validated": non_validated
                }
            ).data,
            status=status.HTTP_200_OK
        )


class ReviewDetailsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch review details as an Admin",
        description="Fetch data for a specific review",
        tags=["Admin"],
        responses=ReviewInfoSerializer,
    )
    def get(self, request, version, pk):
        review = get_object_or_404(Review, pk=pk)

        return Response(
            ReviewInfoSerializer(
                instance=review,
            ).data,
            status=status.HTTP_200_OK
        )


class ExportMapAPI(APIView):

    @extend_schema(
        summary="Export Public Map",
        description=(
            "Export published map as GeoJSON, Shapefile, PNG, or SVG."
        ),
        tags=["Map"],
        parameters=[
            OpenApiParameter(
                name="export_type",
                default=ExportMapTypes.geojson,
                required=False,
                enum=ExportMapTypes.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiTypes.BINARY,  # Binary response for file downloads
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        if publication.status != PublicationStatus.published:
            raise ValidationError({
                "message": "Map not yet published"
            })

        # Validate the requested format
        serializer = ExportMapSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError({
                "message": "Invalid format parameter."
            })

        try:
            # Get the requested format from query parameters
            type = serializer.validated_data.get(
                "export_type",
                ExportMapTypes.geojson
            )

            # Load your GeoDataFrame
            gdf = self._load_geodataframe(publication.validated_values)

            # Handle the export based on the requested format
            year_month = publication.year_month.strftime('%Y-%m')
            if type == ExportMapTypes.geojson:
                return self._export_geojson(gdf, year_month)
            elif type == ExportMapTypes.shapefile:
                return self._export_shapefile(gdf, year_month)
            elif type == ExportMapTypes.png:
                return self._export_image(gdf, year_month, "png")
            elif type == ExportMapTypes.svg:
                return self._export_image(gdf, year_month, "svg")
        except Exception as e:
            return Response(
                {
                    "message": f"An error occurred during export: {e}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _load_geodataframe(self, validated_values):
        # Step 1: Load the TopoJSON file
        with open("./source/country.topojson", "r") as f:
            topojson_data = json.load(f)
        validated_dict = {
            item["administration_id"]: item["category"]
            for item in validated_values
        }
        # Step 2: Convert TopoJSON to GeoJSON using the topojson library.
        # The country file has a single named object; use whatever it is
        # named (e.g. "eswatini", "kenya", "data") so this works for any
        # country, not just Eswatini.
        object_names = list(topojson_data.get("objects", {}).keys())
        if not object_names:
            raise ValueError("No objects found in source/country.topojson")
        topology = tp.Topology(topojson_data, object_name=object_names[0])
        # Convert the TopoJSON to GeoJSON
        geojson_data = topology.to_geojson()

        # Step 3: Load the GeoJSON data into a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(json.loads(geojson_data))

        # Step 4: Map the categories to the GeoDataFrame
        gdf["category"] = gdf["administration_id"].map(validated_dict)

        # Step 5: Add the "cat_name" column
        gdf["cat_name"] = gdf["category"].map(
            DroughtCategory.FieldStr.get
        )

        # Step 6: Handle missing values (optional)
        gdf["category"] = gdf["category"].fillna(DroughtCategory.none)
        gdf["cat_name"] = gdf["cat_name"].fillna(
            DroughtCategory.FieldStr[DroughtCategory.none]
        )
        # Ensure the GeoDataFrame has a CRS
        if gdf.crs is None:
            # Assign a default CRS (e.g., WGS84, EPSG:4326)
            gdf.set_crs("EPSG:4326", inplace=True)
        return gdf

    def _export_geojson(self, gdf, year_month):
        """
        Export the GeoDataFrame as GeoJSON.
        """
        geojson_data = gdf.to_json()
        response = HttpResponse(geojson_data, content_type="application/json")
        cd = f'attachment; filename="cdi_map_{year_month}.geojson"'
        response["Content-Disposition"] = cd
        return response

    def _export_shapefile(self, gdf, year_month):
        """
        Export the GeoDataFrame as a Shapefile (zipped).
        """
        # Rename `administration_id` column to `adm_id` in gdf
        gdf = gdf.rename(columns={"administration_id": "adm_id"})

        # Create an in-memory buffer for the Shapefile
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            # Write the Shapefile components to the zip file
            temp_dir = "./tmp"
            os.makedirs(
                temp_dir,
                exist_ok=True
            )
            gdf.to_file(
                os.path.join(temp_dir, f"cdi_map_{year_month}.shp"),
                driver="ESRI Shapefile"
            )
            # Manually create the .prj file if it doesn't exist
            prj_path = os.path.join(
                temp_dir,
                f"cdi_map_{year_month}.prj"
            )
            if not os.path.exists(prj_path):
                with open(prj_path, "w") as prj_file:
                    prj_file.write(gdf.crs.to_wkt())

            for ext in ["shp", "shx", "dbf", "prj"]:
                file_path = os.path.join(
                    temp_dir,
                    f"cdi_map_{year_month}.{ext}"
                )
                zip_file.write(
                    file_path,
                    arcname=f"cdi_map_{year_month}.{ext}"
                )
                os.remove(file_path)  # Clean up temporary files

        # Prepare the HTTP response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type="application/zip")
        cd = f'attachment; filename="cdi_map_{year_month}.zip"'
        response["Content-Disposition"] = cd
        return response

    def _export_image(self, gdf, year_month, format):
        """
        Export the GeoDataFrame as an image (SVG or PNG).
        """
        if format not in ["svg", "png"]:
            raise ValidationError({
                "message": (
                    "Invalid format parameter."
                    "Only 'svg' and 'png' are supported."
                )
            })

        # Define a custom color mapping for categories
        color_mapping = dict(DroughtCategoryColor.FieldStr.items())

        # Ensure valid geometries
        gdf = gdf[gdf.is_valid & ~gdf.geometry.is_empty]

        fig, ax = plt.subplots(figsize=(10, 10))

        # Plot
        valid_categories = set(gdf["category"].unique())
        filtered_color_mapping = {
            k: v for k, v in color_mapping.items() if k in valid_categories
        }

        legend_patches = []  # Store patches for the legend
        for category, color in filtered_color_mapping.items():
            subset = gdf[gdf["category"] == category]
            subset.plot(
                ax=ax,
                color=color,
                edgecolor="black",
                label=DroughtCategory.FieldStr.get(category)
            )

            legend_patches.append(Patch(
                facecolor=color,
                edgecolor="black",
                label=DroughtCategory.FieldStr.get(category)
            ))

        # Fix aspect ratio and limits
        ax.set_xlim(gdf.total_bounds[0], gdf.total_bounds[2])
        ax.set_ylim(gdf.total_bounds[1], gdf.total_bounds[3])

        # Add legend to the plot
        if legend_patches:
            ax.legend(
                handles=legend_patches,
                loc="upper right",
                title="Drought Categories"
            )

        # Save as image
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format=format, bbox_inches="tight")
        plt.close(fig)

        img_buffer.seek(0)
        content_type = "image/svg+xml" if format == "svg" else "image/png"
        response = HttpResponse(img_buffer, content_type=content_type)
        cd = f'attachment; filename="cdi_map_{year_month}.{format}"'
        response["Content-Disposition"] = cd
        return response


class PublishedMapViewSet(viewsets.ModelViewSet):
    serializer_class = PublishedMapSerializer
    pagination_class = Pagination

    def get_queryset(self):
        return Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False
        ).order_by("-year_month")

    @extend_schema(
        responses={200: PublishedMapSerializer},
        tags=["Map"],
        description="Published maps list",
        parameters=[
            OpenApiParameter(
                name="left_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="right_date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Override the list method to add extra context.
        """
        serializer = CompareMapSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"message": validate_serializers_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Paginate the queryset
        queryset = self.get_queryset()
        left_date = serializer.validated_data.get("left_date")
        right_date = serializer.validated_data.get("right_date")
        if left_date and right_date:
            queryset = queryset.filter(
                year_month__in=[left_date, right_date]
            )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page,
            many=True,
        )
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        responses={200: PublishedMapSerializer},
        tags=["Map"],
        description="Published Map details",
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PublicationDateAPI(APIView):

    @extend_schema(
        description="Fetch all publication date of published maps",
        tags=["Map"],
        parameters=[
            OpenApiParameter(
                name="exclude_id",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses=CommonOptionSerializer,
    )
    def get(self, request, version):
        queryset = Publication.objects.filter(
            status=PublicationStatus.published,
            published_at__isnull=False
        ).order_by("-year_month")
        exclude_id = request.GET.get("exclude_id")
        if exclude_id:
            queryset = queryset.exclude(pk=int(exclude_id))
        publications = queryset.all()
        options = [
            {
                "value": p.id,
                "label": p.year_month
            }
            for p in publications
        ]
        return Response(
            CommonOptionSerializer(
                instance=options,
                many=True,
            ).data,
            status=status.HTTP_200_OK
        )


class RasterPushAPI(APIView):
    """Native pipeline push of a raster asset onto the platform (DIH-1).

    Key-only (HasApiKey); upserts the core ``Raster`` by ``geonode_id`` with
    the metadata and the pipeline-reduced per-administration ``values``. Core
    and always available: it does not depend on the optional geonode module,
    so the publication workflow gets its data without any external raster
    store.
    """

    authentication_classes = []
    permission_classes = [HasApiKey]

    @extend_schema(
        summary="Push a raster asset to the platform",
        tags=["Pipeline"],
        request=RasterPushSerializer,
        responses={
            200: RasterPushResponseSerializer,
            201: RasterPushResponseSerializer,
            403: DefaultResponseSerializer,
        },
    )
    def post(self, request, version):
        serializer = RasterPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        # ponytail: keyed on geonode_id (the pipeline uploads to GeoNode first,
        # so it always has one). A geonode-less pipeline would key on
        # category+year_month — add that when such a pipeline exists.
        defaults = {
            "category": d["category"],
            "title": d["title"],
            "year_month": d["year_month"],
        }
        # Only overwrite values/resource_created when the push carries them, so
        # a metadata-only re-push does not wipe previously pushed values.
        if "values" in d:
            defaults["values"] = d["values"]
        if "resource_created" in d:
            defaults["resource_created"] = d["resource_created"]
        raster, created = Raster.objects.update_or_create(
            geonode_id=d["geonode_id"], defaults=defaults,
        )
        http_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(
            {
                "id": raster.pk,
                "geonode_id": raster.geonode_id,
                "synced_at": raster.synced_at,
            },
            status=http_status,
        )


class RasterListAPI(APIView):
    """Admin publication picker, served from the platform ``Raster`` assets.

    Core and always available: a pure DB read that never depends on GeoNode.
    A raster's started publication is found via the ``Raster.publication``
    OneToOne (``raster_id``), not any GeoNode id. URL pointers are GeoNode
    enrichment (optional module) and are null here.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def _serialize(self, raster, pub, gnr=None):
        return {
            "pk": raster.pk,
            "geonode_id": raster.geonode_id,
            "title": raster.title,
            "detail_url": gnr.detail_url if gnr else None,
            "embed_url": gnr.embed_url if gnr else None,
            "thumbnail_url": gnr.thumbnail_url if gnr else None,
            "download_url": gnr.download_url if gnr else None,
            "created": raster.resource_created,
            "year_month": pub.year_month if pub else raster.year_month,
            "publication_id": pub.pk if pub else None,
            "status": pub.status if pub else None,
        }

    @staticmethod
    def _geonode_pointers(raster_ids):
        """Map raster_id -> GeoNodeResource from the optional geonode module.

        Empty when the module is off, so the core listing stays independent
        and the URL pointers simply stay null.
        """
        if not raster_ids or not module_enabled("geonode"):
            return {}
        from django.apps import apps
        try:
            model = apps.get_model("v1_geonode", "GeoNodeResource")
        except LookupError:
            return {}
        return {
            g.raster_id: g
            for g in model.objects.filter(raster_id__in=raster_ids)
        }

    @extend_schema(
        summary="List CDI raster assets for the publication picker",
        tags=["Admin"],
        parameters=[
            OpenApiParameter(
                name="page", default=1, required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="category", default=CDIGeonodeCategory.cdi,
                required=False, enum=CDIGeonodeCategory.FieldStr.keys(),
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="status", required=False,
                enum=PublicationStatus.FieldStr.keys(),
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="id", required=False, type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: RasterListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        serializer = RasterFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            raise ValidationError({"message": "Invalid filter parameter."})
        data = serializer.validated_data

        # Single-resource lookup by Raster id.
        if data.get("id"):
            raster = Raster.objects.filter(pk=data["id"]).first()
            if not raster:
                return Response(
                    {"message": "Raster not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            pub = Publication.objects.filter(raster_id=raster.pk).first()
            gnr = self._geonode_pointers([raster.pk]).get(raster.pk)
            return Response(
                RasterListSerializer(
                    self._serialize(raster, pub, gnr)
                ).data,
                status=status.HTTP_200_OK,
            )

        # List by category (+ optional publication status filter).
        category = data.get("category", CDIGeonodeCategory.cdi)
        publication_status = data.get("status")
        page = int(request.GET.get("page", "1"))
        page_size = 10

        rows = list(
            Raster.objects.filter(category=category).order_by("-year_month")
        )
        pubs = {
            p.raster_id: p
            for p in Publication.objects.filter(
                raster_id__in=[r.pk for r in rows]
            )
        }
        if publication_status is not None:
            rows = [
                r for r in rows
                if pubs.get(r.pk)
                and pubs[r.pk].status == publication_status
            ]
        pointers = self._geonode_pointers([r.pk for r in rows])
        items = [
            self._serialize(r, pubs.get(r.pk), pointers.get(r.pk))
            for r in rows
        ]

        total = len(items)
        total_page = ceil(total / page_size) if total else 0
        start = (page - 1) * page_size
        page_items = items[start:start + page_size]
        return Response(
            {
                "current": page,
                "total": total,
                "total_page": total_page,
                "data": RasterListSerializer(
                    instance=page_items, many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )
