from enum import Enum


class UserRoleTypes:
    admin = 1
    reviewer = 2

    FieldStr = {
        admin: "Admin",
        reviewer: "Reviewer",
    }


class ActionEnum(Enum):
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name.capitalize()) for tag in cls]
