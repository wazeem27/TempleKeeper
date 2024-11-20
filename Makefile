# Makefile for Django project management

# Variables
DJANGO_MANAGE=python3 manage.py

# Targets
.PHONY: delete_migrations makemigrations migrate all

# Target to delete all migrations

# Target to make migrations
makemigrations:
	$(DJANGO_MANAGE) makemigrations temple_inventory offering_services temple_auth billing_manager
	$(DJANGO_MANAGE) migrate

permissions:
	$(DJANGO_MANAGE) create_permissions
	$(DJANGO_MANAGE) create_sample_temples
	$(DJANGO_MANAGE) create_user

delete_db:
	rm db.sqlite3

load_inventories:
	$(DJANGO_MANAGE) load_inventory

load_vazhipadu:
	$(DJANGO_MANAGE) load_vazhipadu_offerings

load_stars:
	$(DJANGO_MANAGE) load_stars

delete_migrations:
	rm -rf temple_auth/migrations
	rm -rf temple_inventory/migrations
	rm -rf billing_manager/migrations
	rm -rf offering_services/migrations

# Target to delete migrations, make migrations, and migrate
all: delete_migrations makemigrations permissions load_inventories load_vazhipadu load_stars

