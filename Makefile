# Makefile for Django project management

# Variables
DJANGO_MANAGE=python3 manage.py

# Targets
.PHONY: delete_migrations makemigrations migrate all

# Target to delete all migrations
delete_migrations:
	find . -path "*/migrations/*" -type d -exec rm -rf {} +

# Target to make migrations
makemigrations:
	$(DJANGO_MANAGE) makemigrations temple_inventory offering_services temple_services temple_auth billing_manager
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

# Target to delete migrations, make migrations, and migrate
all: delete_migrations makemigrations

