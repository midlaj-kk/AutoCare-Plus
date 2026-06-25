JOB_STATUS_WAITING = "waiting"
JOB_STATUS_IN_PROGRESS = "in_progress"
JOB_STATUS_WAITING_FOR_PARTS = "waiting_for_parts"
JOB_STATUS_QC_PENDING = "qc_pending"
JOB_STATUS_REWORK_REQUIRED = "rework_required"
JOB_STATUS_READY_FOR_BILL = "ready_for_bill"
JOB_STATUS_READY_FOR_DELIVERY = "ready_for_delivery"
JOB_STATUS_DELIVERED = "delivered"
JOB_STATUS_CANCELLED = "cancelled"

JOB_STATUS_CHOICES = [
    (JOB_STATUS_WAITING, "Waiting"),
    (JOB_STATUS_IN_PROGRESS, "In Progress"),
    (JOB_STATUS_WAITING_FOR_PARTS, "Waiting for Parts"),
    (JOB_STATUS_QC_PENDING, "QC Pending"),
    (JOB_STATUS_REWORK_REQUIRED, "Rework Required"),
    (JOB_STATUS_READY_FOR_BILL, "Ready for Bill"),
    (JOB_STATUS_READY_FOR_DELIVERY, "Ready for Delivery"),
    (JOB_STATUS_DELIVERED, "Delivered"),
    (JOB_STATUS_CANCELLED, "Cancelled"),
]

WORK_STATUS_PENDING = "pending"
WORK_STATUS_IN_PROGRESS = "in_progress"
WORK_STATUS_COMPLETED = "completed"

WORK_STATUS_CHOICES = [
    (WORK_STATUS_PENDING, "Pending"),
    (WORK_STATUS_IN_PROGRESS, "In Progress"),
    (WORK_STATUS_COMPLETED, "Completed"),
]

QC_PASSED = "passed"
QC_FAILED = "failed"
QC_NA = "na"

QC_OVERALL_APPROVED = "approved"
QC_OVERALL_REWORK = "rework_required"

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_PARTIAL = "partial"

MOVEMENT_IN = "in"
MOVEMENT_OUT = "out"
