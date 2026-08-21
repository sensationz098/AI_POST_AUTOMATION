from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.publishing_batch import PublishingBatch, PublishingJob, BatchStatus, JobStatus
from datetime import datetime, timezone

class PublishingRepository:
    def create_batch(
        self,
        db: Session,
        post_id: int,
        user_id: int,
        total_targets: int,
        idempotency_key: Optional[str] = None
    ) -> PublishingBatch:
        if idempotency_key:
            existing = db.query(PublishingBatch).filter(
                PublishingBatch.idempotency_key == idempotency_key
            ).first()
            if existing:
                return existing

        batch = PublishingBatch(
            post_id=post_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            status=BatchStatus.QUEUED.value,
            total_targets=total_targets,
            successful_targets=0,
            failed_targets=0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    def create_job(
        self,
        db: Session,
        batch_id: int,
        social_account_id: int,
        platform: str
    ) -> PublishingJob:
        job = PublishingJob(
            batch_id=batch_id,
            social_account_id=social_account_id,
            platform=platform,
            status=JobStatus.QUEUED.value,
            attempts=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_batch(self, db: Session, batch_id: int) -> Optional[PublishingBatch]:
        return db.query(PublishingBatch).filter(PublishingBatch.id == batch_id).first()

    def update_job_status(
        self,
        db: Session,
        job_id: int,
        status: str,
        external_post_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[PublishingJob]:
        job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
        if job:
            job.status = status
            job.attempts += 1
            if external_post_id:
                job.external_post_id = external_post_id
            if error_code:
                job.error_code = error_code
            if error_message:
                job.error_message = error_message
            if status == JobStatus.SUCCESS.value:
                job.published_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(job)
        return job

    def update_batch_summary(self, db: Session, batch_id: int) -> Optional[PublishingBatch]:
        db.expire_all()
        batch = self.get_batch(db, batch_id)
        if not batch:
            return None

        jobs = db.query(PublishingJob).filter(PublishingJob.batch_id == batch_id).all()
        total_jobs = len(jobs)
        success_count = sum(1 for j in jobs if j.status == JobStatus.SUCCESS.value)
        failed_count = sum(1 for j in jobs if j.status == JobStatus.FAILED.value)
        processing_count = sum(1 for j in jobs if j.status in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value, JobStatus.RETRYING.value])

        batch.total_targets = total_jobs if total_jobs > 0 else batch.total_targets
        batch.successful_targets = success_count
        batch.failed_targets = failed_count

        now_utc = datetime.now(timezone.utc)
        if processing_count > 0:
            batch.status = BatchStatus.PROCESSING.value
        elif total_jobs > 0 and success_count == total_jobs:
            batch.status = BatchStatus.SUCCESS.value
            batch.completed_at = now_utc
        elif success_count > 0 and failed_count > 0:
            batch.status = BatchStatus.PARTIAL_SUCCESS.value
            batch.completed_at = now_utc
        elif total_jobs > 0 and failed_count == total_jobs:
            batch.status = BatchStatus.FAILED.value
            batch.completed_at = now_utc
        else:
            batch.status = BatchStatus.FAILED.value
            batch.completed_at = now_utc

        db.commit()
        db.refresh(batch)
        return batch


publishing_repo = PublishingRepository()
