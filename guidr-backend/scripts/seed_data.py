"""Script to seed institutions and programs data."""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import src
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from src.db import SessionLocal, engine, Base
from src.models.institution import Institution
from src.models.program import Program
from src.models.program_tag import ProgramTag
from src.utils.data_completeness import calculate_program_completeness
from datetime import datetime

# Create tables
Base.metadata.create_all(bind=engine)


def load_json(filepath: Path):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def seed_institutions(db: Session, data_dir: Path):
    """Seed institutions from JSON file."""
    institutions_data = load_json(data_dir / "seed_institutions.json")
    institutions_map = {}
    
    for inst_data in institutions_data:
        # Check if institution already exists
        existing = db.query(Institution).filter(
            Institution.name == inst_data["name"]
        ).first()
        
        if existing:
            institutions_map[inst_data["name"]] = existing
            continue
        
        institution = Institution(
            name=inst_data["name"],
            short_name=inst_data.get("short_name"),
            country=inst_data["country"],
            state_or_province=inst_data.get("state_or_province"),
            city=inst_data.get("city"),
            website_url=inst_data.get("website_url"),
            institution_type=inst_data.get("institution_type"),
            public_private=inst_data.get("public_private"),
            overall_rank=inst_data.get("overall_rank"),
        )
        db.add(institution)
        db.flush()
        institutions_map[inst_data["name"]] = institution
    
    db.commit()
    return institutions_map


def seed_programs(db: Session, data_dir: Path, institutions_map: dict):
    """Seed programs from JSON file."""
    programs_data = load_json(data_dir / "seed_programs.json")
    
    for prog_data in programs_data:
        institution = institutions_map.get(prog_data["institution_name"])
        if not institution:
            print(f"Warning: Institution '{prog_data['institution_name']}' not found, skipping program")
            continue
        
        # Check if program already exists
        existing = db.query(Program).filter(
            Program.name == prog_data["name"],
            Program.institution_id == institution.id
        ).first()
        
        if existing:
            continue
        
        from decimal import Decimal
        from datetime import datetime as dt
        
        program = Program(
            institution_id=institution.id,
            name=prog_data["name"],
            degree_level=prog_data["degree_level"],
            delivery_mode=prog_data.get("delivery_mode"),
            field_of_study=prog_data.get("field_of_study"),
            research_or_coursework=prog_data.get("research_or_coursework"),
            description=prog_data.get("description"),
            application_deadline_primary=dt.fromisoformat(prog_data["application_deadline_primary"]).date() if prog_data.get("application_deadline_primary") else None,
            tuition_estimate_per_year=Decimal(str(prog_data["tuition_estimate_per_year"])) if prog_data.get("tuition_estimate_per_year") else None,
            application_fee=Decimal(str(prog_data["application_fee"])) if prog_data.get("application_fee") else None,
            website_url=prog_data.get("website_url"),
            program_features=prog_data.get("program_features"),
        )
        db.add(program)
        db.flush()

        program.data_completeness_score = calculate_program_completeness(
            {
                "name": program.name,
                "degree_level": program.degree_level,
                "institution_id": str(program.institution_id),
                "description": program.description,
                "application_deadline_primary": program.application_deadline_primary,
                "tuition_estimate_per_year": program.tuition_estimate_per_year,
                "program_features": program.program_features,
            }
        )
        
        # Add tags from program_features
        if prog_data.get("program_features"):
            for feature in prog_data["program_features"]:
                tag = ProgramTag(
                    program_id=program.id,
                    tag_type="keyword",
                    value=feature
                )
                db.add(tag)
    
    db.commit()


def main():
    """Main seeding function."""
    data_dir = Path(__file__).parent.parent / "data"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)
    
    db = SessionLocal()
    try:
        print("Seeding institutions...")
        institutions_map = seed_institutions(db, data_dir)
        print(f"Seeded {len(institutions_map)} institutions")
        
        print("Seeding programs...")
        seed_programs(db, data_dir, institutions_map)
        print("Seeded programs")
        
        print("Seeding complete!")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

