from enum import Enum


class UserRoleTypes:
    admin = 1
    reviewer = 2

    FieldStr = {
        admin: "Admin",
        reviewer: "Reviewer",
    }


# Technical Working Group list
# https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT?node-id=3-2#1050735747
class TechnicalWorkingGroup:
    ndma = 1
    moag = 2
    met = 3
    dwa = 4
    uneswa = 5

    FieldStr = {
        ndma: "NDMA (National Disaster Management Agency)",
        moag: "MoAg (Ministry of Agriculture)",
        met: "MET (Meteorological Office)",
        dwa: "DWA (Department of Water Affairs)",
        uneswa: "UNESWA (University of Eswatini)",
    }


class ActionEnum(Enum):
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]
