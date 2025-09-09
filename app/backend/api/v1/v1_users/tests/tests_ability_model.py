from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
from api.v1.v1_users.models import Ability, ActionEnum, UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class AbilityModelTestCase(TestCase):
    def test_create_ability(self):
        # Create an ability for the Admin role
        ability = Ability.objects.create(
            role=UserRoleTypes.admin,
            action=ActionEnum.CREATE.value,
            subject="Publication",
            conditions={"owner": True},
        )
        self.assertEqual(ability.role, UserRoleTypes.admin)
        self.assertEqual(ability.action, ActionEnum.CREATE.value)
        self.assertEqual(ability.subject, "Publication")
        self.assertEqual(ability.conditions, {"owner": True})

    def test_conditions_field_accepts_null(self):
        # Create an ability without conditions
        ability = Ability.objects.create(
            role=UserRoleTypes.admin,
            action=ActionEnum.READ.value,
            subject="Review",
        )
        self.assertIsNone(ability.conditions)

    def test_unique_together_constraint(self):
        # Create an ability
        Ability.objects.create(
            role=UserRoleTypes.reviewer,
            action=ActionEnum.READ.value,
            subject="Publication",
        )
        # Attempt to create a duplicate ability
        with self.assertRaises(Exception):
            Ability.objects.create(
                role=UserRoleTypes.reviewer,
                action=ActionEnum.READ.value,
                subject="Publication",
            )

    def test_str_representation(self):
        # Create an ability
        ability = Ability.objects.create(
            role=UserRoleTypes.admin,
            action=ActionEnum.UPDATE.value,
            subject="Review",
        )
        self.assertEqual(
            str(ability),
            f"{UserRoleTypes.admin}: {ability.action} {ability.subject}"
        )

    def test_valid_action_choices(self):
        # Test invalid action
        invalid_ability = Ability(
            role=UserRoleTypes.reviewer,
            action="INVALID_ACTION",
            subject="Review",
        )
        with self.assertRaises(ValidationError) as context:
            invalid_ability.clean()
        self.assertIn("action", context.exception.error_dict)
        self.assertIn(
            "'INVALID_ACTION' is not a valid action.",
            context.exception.error_dict["action"][0]
        )

    def test_roles_n_abilities_seeder(self):
        call_command(
            "generate_roles_n_abilities_seeder"
        )
        self.assertEqual(Ability.objects.count(), 12)
