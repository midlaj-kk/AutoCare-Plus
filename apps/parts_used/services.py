from apps.inventory.services import consume_part, restore_part


def add_part_used(service_job, spare_part_id, quantity, actor):
    return consume_part(service_job, spare_part_id, quantity, actor)


def remove_part_used(part_used, actor):
    restore_part(part_used, actor)
