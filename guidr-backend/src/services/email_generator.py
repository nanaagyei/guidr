"""Email generation service for creating personalized cold email drafts."""
from typing import Optional, Dict, Any
from src.models.professor import Professor
from src.models.user_profile import UserProfile
from src.models.academic_record import AcademicRecord
from src.models.program import Program
from src.models.institution import Institution


def generate_cold_email(
    professor: Professor,
    user_profile: UserProfile,
    academic_record: Optional[AcademicRecord],
    program: Optional[Program] = None
) -> tuple[str, str]:
    """Generate a personalized cold email draft.

    Args:
        professor: Professor to email
        user_profile: User's profile
        academic_record: User's academic record (latest)
        program: Optional program context

    Returns:
        Tuple of (subject, body)
    """
    # Extract user info
    user_name = getattr(user_profile, '_user_name', None) or "Student"
    user_field = user_profile.primary_field_of_study or "my field"

    # Extract professor info
    professor_name = professor.full_name
    professor_title = professor.title or "Professor"

    # Build subject line
    if program:
        subject = f"Inquiry about {program.name} and Research Opportunities"
    else:
        subject = f"Inquiry about Research Opportunities in {user_field}"

    # Build email body
    greeting = f"Dear {professor_title} {professor_name.split()[-1]}"  # Use last name

    intro = f"My name is {user_name}, and I am a prospective graduate student interested in {user_field}."

    # Research interest paragraph
    research_interest = ""
    if professor.research_summary:
        research_interest = f"I was particularly interested in your research on {professor.research_summary[:100]}... "
    elif professor.interests_tags:
        tags = professor.interests_tags[:3] if isinstance(professor.interests_tags, list) else []
        if tags:
            research_interest = f"Your work in {', '.join(tags)} aligns closely with my research interests. "

    # Academic background
    academic_background = ""
    if academic_record:
        institution = academic_record.institution_name
        degree = academic_record.degree_level.capitalize() if academic_record.degree_level else "degree"
        field = academic_record.field_of_study or user_field

        academic_background = f"I am currently completing (or have completed) a {degree} in {field} from {institution}. "

        if academic_record.normalized_gpa:
            academic_background += f"I have maintained a GPA of {academic_record.normalized_gpa:.2f}/4.0. "

    # Program-specific paragraph
    program_context = ""
    if program:
        program_context = f"I am particularly interested in the {program.name} program at {program.institution.name if program.institution else 'your institution'}. "

    # Interest statement
    interest_statement = f"I am eager to learn more about potential research opportunities in your lab and would appreciate the chance to discuss how my background and interests might align with your ongoing projects."

    # Closing
    closing = f"I have attached my resume for your review. Thank you for considering my inquiry, and I look forward to hearing from you."
    signature = f"\n\nBest regards,\n{user_name}"

    # Compose body
    body = f"""{greeting},

{intro} {research_interest}

{academic_background}{program_context}

{interest_statement}

{closing}{signature}"""

    return subject, body


def generate_email_template_simple(
    professor: Professor,
    user_name: str,
    user_field: str
) -> tuple[str, str]:
    """Generate a simple email template (fallback).

    Args:
        professor: Professor to email
        user_name: User's name
        user_field: User's field of study

    Returns:
        Tuple of (subject, body)
    """
    subject = f"Inquiry about Research Opportunities in {user_field}"

    professor_last_name = professor.full_name.split()[-1]
    greeting = f"Dear Dr. {professor_last_name}"

    body = f"""{greeting},

My name is {user_name}, and I am a prospective graduate student interested in {user_field}.

I came across your profile and was intrigued by your research work. I would love to learn more about potential research opportunities in your lab.

I have attached my resume and academic transcript for your review. Thank you for your time and consideration.

Best regards,
{user_name}"""

    return subject, body
