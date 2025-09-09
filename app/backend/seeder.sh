#!/usr/bin/env bash

echo "Seed Administration? [y/n]"
read -r seed_administration
if [[ "${seed_administration}" == 'y' || "${seed_administration}" == 'Y' ]]; then
    python manage.py generate_administrations_seeder
fi

echo "Seed Role and Abilities? [y/n]"
read -r seed_role_abilities
if [[ "${seed_role_abilities}" == 'y' || "${seed_role_abilities}" == 'Y' ]]; then
    python manage.py generate_roles_n_abilities_seeder
fi

echo "Add New Super Admin? [y/n]"
read -r add_account
if [[ "${add_account}" == 'y' || "${add_account}" == 'Y' ]]; then
    echo "Please type email address"
    read -r email_address
    if [[ "${email_address}" != '' ]]; then
        python manage.py createsuperuser --email "${email_address}" --role 1
    fi
fi

echo "Seed Fake User? [y/n]"
read -r fake_user
if [[ "${fake_user}" == 'y' || "${fake_user}" == 'Y' ]]; then
    python manage.py generate_admin_seeder
    python manage.py fake_users_seeder
fi

echo "Seed Fake Data? [y/n]"
read -r seed_fake_data
if [[ "${seed_fake_data}" == 'y' || "${seed_fake_data}" == 'Y' ]]; then
    python manage.py fake_publications_seeder
fi

python manage.py generate_config
