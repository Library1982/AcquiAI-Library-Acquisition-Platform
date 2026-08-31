from database import Base, engine
import models

print("Creating AcquiAI database...")

Base.metadata.create_all(bind=engine)

print("AcquiAI database created successfully.")