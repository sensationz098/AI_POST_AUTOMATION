from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.models.youtube_upload import YouTubeUpload, YouTubeUploadStatus

class YouTubeUploadRepository:
    def create(
        self,
        db: Session,
        upload_id: str,
        user_id: int,
        social_account_id: int,
        channel_id: str,
        title: str,
        file_size_bytes: int,
        description: Optional[str] = "",
        privacy_status: str = "private",
        original_filename: Optional[str] = None,
        mime_type: str = "video/mp4",
        encrypted_session_url: Optional[str] = None,
        client_mutation_id: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> YouTubeUpload:
        # Pre-check for existing active upload if client_mutation_id is given
        if client_mutation_id:
            existing = self.get_by_mutation_id(db, user_id, client_mutation_id)
            if existing:
                return existing

        upload = YouTubeUpload(
            upload_id=upload_id,
            client_mutation_id=client_mutation_id,
            user_id=user_id,
            social_account_id=social_account_id,
            channel_id=channel_id,
            title=title,
            description=description or "",
            privacy_status=privacy_status or "private",
            original_filename=original_filename,
            mime_type=mime_type or "video/mp4",
            file_size_bytes=file_size_bytes,
            bytes_uploaded=0,
            progress_percentage=0.0,
            upload_status=YouTubeUploadStatus.INITIATED.value,
            encrypted_session_url=encrypted_session_url,
            metadata_json=metadata_json or {},
        )
        db.add(upload)
        try:
            db.commit()
            db.refresh(upload)
            return upload
        except Exception:
            db.rollback()
            if client_mutation_id:
                existing = self.get_by_mutation_id(db, user_id, client_mutation_id)
                if existing:
                    return existing
            raise

    def get_by_upload_id(self, db: Session, upload_id: str) -> Optional[YouTubeUpload]:
        return db.query(YouTubeUpload).filter(YouTubeUpload.upload_id == upload_id).first()

    def get_by_upload_id_and_user(self, db: Session, upload_id: str, user_id: int) -> Optional[YouTubeUpload]:
        return db.query(YouTubeUpload).filter(
            YouTubeUpload.upload_id == upload_id,
            YouTubeUpload.user_id == user_id
        ).first()

    def get_by_mutation_id(self, db: Session, user_id: int, client_mutation_id: str) -> Optional[YouTubeUpload]:
        return db.query(YouTubeUpload).filter(
            YouTubeUpload.user_id == user_id,
            YouTubeUpload.client_mutation_id == client_mutation_id,
            YouTubeUpload.upload_status.notin_([YouTubeUploadStatus.FAILED.value, YouTubeUploadStatus.CANCELLED.value])
        ).order_by(YouTubeUpload.created_at.desc()).first()

    def list_by_user(self, db: Session, user_id: int, limit: int = 20, offset: int = 0) -> List[YouTubeUpload]:
        return db.query(YouTubeUpload).filter(
            YouTubeUpload.user_id == user_id
        ).order_by(YouTubeUpload.created_at.desc()).offset(offset).limit(limit).all()

    def update_progress(
        self,
        db: Session,
        upload_id: str,
        bytes_uploaded: int,
        total_bytes: int,
        status: str = YouTubeUploadStatus.UPLOADING.value
    ) -> Optional[YouTubeUpload]:
        upload = self.get_by_upload_id(db, upload_id)
        if not upload:
            return None
        
        pct = round((bytes_uploaded / total_bytes * 100.0), 2) if total_bytes > 0 else 0.0
        upload.bytes_uploaded = bytes_uploaded
        upload.progress_percentage = min(pct, 100.0)
        upload.upload_status = status
        upload.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(upload)
        return upload

    def mark_completed(
        self,
        db: Session,
        upload_id: str,
        video_id: str,
        video_url: str,
    ) -> Optional[YouTubeUpload]:
        upload = self.get_by_upload_id(db, upload_id)
        if not upload:
            return None

        now = datetime.now(timezone.utc)
        upload.video_id = video_id
        upload.video_url = video_url
        upload.bytes_uploaded = upload.file_size_bytes
        upload.progress_percentage = 100.0
        upload.upload_status = YouTubeUploadStatus.PROCESSING.value
        upload.processing_status = "processing"
        upload.completed_at = now
        upload.updated_at = now
        db.commit()
        db.refresh(upload)
        return upload

    def mark_processing_status(
        self,
        db: Session,
        upload_id: str,
        processing_status: str,
        upload_status: str,
        failure_reason: Optional[str] = None,
    ) -> Optional[YouTubeUpload]:
        upload = self.get_by_upload_id(db, upload_id)
        if not upload:
            return None

        now = datetime.now(timezone.utc)
        upload.processing_status = processing_status
        upload.upload_status = upload_status
        if failure_reason:
            upload.processing_failure_reason = failure_reason
            upload.error_message = failure_reason
        upload.updated_at = now
        db.commit()
        db.refresh(upload)
        return upload

    def mark_failed(self, db: Session, upload_id: str, error_message: str) -> Optional[YouTubeUpload]:
        upload = self.get_by_upload_id(db, upload_id)
        if not upload:
            return None

        now = datetime.now(timezone.utc)
        upload.upload_status = YouTubeUploadStatus.FAILED.value
        upload.error_message = error_message
        upload.updated_at = now
        db.commit()
        db.refresh(upload)
        return upload

    def mark_cancelled(self, db: Session, upload_id: str) -> Optional[YouTubeUpload]:
        upload = self.get_by_upload_id(db, upload_id)
        if not upload:
            return None

        now = datetime.now(timezone.utc)
        upload.upload_status = YouTubeUploadStatus.CANCELLED.value
        upload.updated_at = now
        db.commit()
        db.refresh(upload)
        return upload

    def list_pending_processing(self, db: Session, older_than_seconds: int = 15, limit: int = 10) -> List[YouTubeUpload]:
        """Fetch uploads in PROCESSING state that have not been checked recently (fallback poller)."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
        return db.query(YouTubeUpload).filter(
            YouTubeUpload.upload_status == YouTubeUploadStatus.PROCESSING.value,
            YouTubeUpload.video_id.isnot(None),
            YouTubeUpload.updated_at <= cutoff
        ).order_by(YouTubeUpload.updated_at.asc()).limit(limit).all()

youtube_upload_repo = YouTubeUploadRepository()
youtube_upload_repository = youtube_upload_repo
