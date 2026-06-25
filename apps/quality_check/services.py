from .models import QualityCheck
from apps.service_jobs.services import transition_job_status
from core.constants import JOB_STATUS_READY_FOR_BILL, JOB_STATUS_REWORK_REQUIRED


def submit_quality_check(job, qc_data, actor):
    qc = QualityCheck.objects.create(service_job=job, checked_by=actor, **qc_data)
    if qc.overall_status == "approved":
        transition_job_status(job, JOB_STATUS_READY_FOR_BILL, actor)
    else:
        transition_job_status(job, JOB_STATUS_REWORK_REQUIRED, actor)
    return qc


def update_quality_check(qc, data, actor):
    for field, value in data.items():
        setattr(qc, field, value)
    qc.save()

    job = qc.service_job
    if qc.overall_status == "approved":
        transition_job_status(job, JOB_STATUS_READY_FOR_BILL, actor)
    else:
        transition_job_status(job, JOB_STATUS_REWORK_REQUIRED, actor)
    return qc
