from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db import Base
from app.domain.enums import PriorAuthStatus

class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name:  Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[str] = mapped_column(String(10), nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    roles: Mapped[str] = mapped_column(String, nullable=False, default="")

class Coverage(Base):
    __tablename__ = "coverages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    member_id: Mapped[str] = mapped_column(String(64), nullable=False)
    plan: Mapped[str] = mapped_column(String(100), nullable=False)
    payer: Mapped[str] = mapped_column(String(100), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    patient = relationship("Patient")

class PriorAuthRequest(Base):
    __tablename__ = "prior_auth_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    coverage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coverages.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)            # CPT/HCPCS
    diagnosis_codes: Mapped[str] = mapped_column(String(256), default="")    # comma-separated
    status: Mapped[PriorAuthStatus] = mapped_column(SAEnum(PriorAuthStatus), default=PriorAuthStatus.requested)
    disposition: Mapped[str] = mapped_column(String(255), default="")        # brief reason/note
    # TEMPORARILY REMOVED: Provider fields until we can add them to the database
    # provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    # provider_npi: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    patient = relationship("Patient")
    coverage = relationship("Coverage")

class DocumentReference(Base):
    __tablename__ = "document_references"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)

    storage_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    pa_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("prior_auth_requests.id"), nullable=True)
