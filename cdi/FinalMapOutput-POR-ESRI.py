import glob
import datetime
import arcpy
## Change these to match your directory structure. If you are missing directories you will need to create them
map_input_dir = r'./source/mapping/data/'
map_output_dir = r'./source/mapping/output/maps/'
tif_dir = r'./source/output_data/GeoTiffs/'
reglyr = map_input_dir+'Percentile_colors_new.lyr'
region = 'eSwatini'
## Resolution can be changed here
res = 150
map_remote_output_dir = r'//ndmc-webp01/WebArchive/GlobalCDI/'+region+'/'

for typ in ['CDI','LST','NDVI','SPI']:
    print 'Mapping '+typ
    arcpy.env.overwriteOutput = True
    tif_list = glob.glob(tif_dir+typ+'/*.tif')
    #in_tif = tif_list[-1]
    for in_tif in tif_list:
        tif_year = (in_tif[-10:])[0:4]
        if tif_year>"2001":
            int_month = ((in_tif[-10:])[0:6])[-2:]
            monthinteger = int(int_month)
            month = datetime.date(1900, monthinteger, 1).strftime('%b')
            tif_layer = arcpy.mapping.Layer(in_tif)
            ## Change this to 10.x.mxd if not running ArcGIS 10.8 or later
            themxd = map_input_dir+region+'_'+typ+'-10.8.mxd'
            #print themxd
            mxd = arcpy.mapping.MapDocument(themxd)
            df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
            arcpy.mapping.AddLayer(df, tif_layer,"BOTTOM")
            tifLayerw =arcpy.mapping.ListLayers(mxd, "STEP_0303_*.tif", df)
            for mapLayerw in tifLayerw:
                arcpy.ApplySymbologyFromLayer_management (mapLayerw, reglyr)
            mapdate = (arcpy.mapping.ListLayoutElements(mxd,"TEXT_ELEMENT","Date"))[0]
            mapdate.text = month+' '+tif_year
            png_dir = map_output_dir+typ+'/png/'
            pdf_dir = map_output_dir+typ+'/pdf/'
            jpg_dir = map_output_dir+typ+'/jpg/'
            rpng_dir = map_remote_output_dir+typ+'/png/'
            rpdf_dir = map_remote_output_dir+typ+'/pdf/'
            rjpg_dir = map_remote_output_dir+typ+'/jpg/'
            print 'Creating png map'
            arcpy.mapping.ExportToPNG(mxd,png_dir+region+'_'+typ+'_'+tif_year+int_month+'.png',resolution=res)
            arcpy.mapping.ExportToPNG(mxd,rpng_dir+region+'_'+typ+'_'+tif_year+int_month+'.png',resolution=res)
            print 'Creating pdf map'
            arcpy.mapping.ExportToPDF(mxd,pdf_dir+region+'_'+typ+'_'+tif_year+int_month+'.pdf',resolution=res)
            arcpy.mapping.ExportToPDF(mxd,rpdf_dir+region+'_'+typ+'_'+tif_year+int_month+'.pdf',resolution=res)
            print 'Creating jpg map'
            arcpy.mapping.ExportToJPEG(mxd,jpg_dir+region+'_'+typ+'_'+tif_year+int_month+'.jpg',resolution=res)
            arcpy.mapping.ExportToJPEG(mxd,rjpg_dir+region+'_'+typ+'_'+tif_year+int_month+'.jpg',resolution=res)
