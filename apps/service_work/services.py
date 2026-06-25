from .models import ServiceWork


def create_service_work(job, data, created_by):
    data["service_job"] = job
    data["created_by"] = created_by
    return ServiceWork.objects.create(**data)


def update_service_work(work, data):
    for field, value in data.items():
        setattr(work, field, value)
    work.save()
    return work
