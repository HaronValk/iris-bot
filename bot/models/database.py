from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(200))
    role = Column(String(20), default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    name = Column(String(200))
    phone = Column(String(20))
    visits_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    appointments = relationship("Appointment", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    icon = Column(String(10))
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    services = relationship("Service", back_populates="category")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String(300), nullable=False)
    description = Column(Text)
    duration = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    category = relationship("Category", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")

class Master(Base):
    __tablename__ = "masters"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    specialization = Column(Text)
    phone = Column(String(20))
    photo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    appointments = relationship("Appointment", back_populates="master")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    master_id = Column(Integer, ForeignKey("masters.id"), nullable=True)
    datetime = Column(DateTime, nullable=False)
    status = Column(String(20), default="confirmed")
    promo_code = Column(String(50), nullable=True)
    discount = Column(Float, default=0)
    client_name = Column(String(200))
    client_phone = Column(String(20))
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    master = relationship("Master", back_populates="appointments")

class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    promotion_type = Column(String(20), default="percent")
    discount_percent = Column(Float, nullable=True)
    promo_code = Column(String(50), unique=True, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)