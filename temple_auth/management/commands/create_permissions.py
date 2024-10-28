from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Create predefined groups and assign permissions.'

    groups_permissions = {
        'Temple Admin': [
            'temple_inventory.can_add_inventoryitem',
            'temple_inventory.can_change_inventoryitem',
            'temple_inventory.can_delete_inventoryitem',
            'temple_inventory.can_view_inventoryitem',
            'offering_services.can_add_vazhipaduoffering',
            'offering_services.can_change_vazhipaduoffering',
            'offering_services.can_delete_vazhipaduoffering',
            'offering_services.can_view_vazhipaduoffering',
            'billing_manager.can_view_bill',
            'billing_manager.can_add_bill',
            'billing_manager.can_change_bill',
            'billing_manager.can_delete_bill',
        ],
        'Central Admin': [
            'auth.add_user',
            'auth.change_user',
            'auth.delete_user',
            'temple_inventory.can_add_inventoryitem',
            'temple_inventory.can_change_inventoryitem',
            'temple_inventory.can_delete_inventoryitem',
            'temple_inventory.can_view_inventoryitem',
            'offering_services.can_add_vazhipaduoffering',
            'offering_services.can_change_vazhipaduoffering',
            'offering_services.can_delete_vazhipaduoffering',
            'offering_services.can_view_vazhipaduoffering',
            'billing_manager.can_view_bill',
            'billing_manager.can_add_bill',
            'billing_manager.can_change_bill',
            'billing_manager.can_delete_bill',
        ],
        'Billing Assistant': [
            'billing_manager.can_view_bill',
            'billing_manager.can_add_bill',
            'billing_manager.can_change_bill',
            'billing_manager.can_delete_bill',
        ],
    }

    def handle(self, *args, **kwargs):
        for group_name, perms in self.groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {group_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Group {group_name} already exists.'))

            for perm in perms:
                app_label, perm_codename = perm.split('.')
                permission = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=perm_codename
                ).first()

                if permission:
                    group.permissions.add(permission)
                    self.stdout.write(self.style.SUCCESS(f'Assigned permission {perm} to group {group_name}.'))
                else:
                    self.stdout.write(self.style.ERROR(f'Permission {perm} does not exist.'))

        self.stdout.write(self.style.SUCCESS('Finished creating groups and assigning permissions.'))
