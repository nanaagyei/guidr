"""Password strength validation utilities."""
import re
from typing import Dict, Tuple


def check_password_strength(password: str) -> Dict[str, any]:
    """Check password strength and return detailed feedback.

    Args:
        password: Password to check

    Returns:
        Dictionary with:
            - score: 0-4 (0=very weak, 4=very strong)
            - strength: 'very_weak', 'weak', 'fair', 'good', 'very_strong'
            - feedback: List of feedback messages
            - requirements: Dict of requirement checks
    """
    score = 0
    feedback = []
    requirements = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'number': bool(re.search(r'\d', password)),
        'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
    }

    # Length check
    if len(password) < 8:
        feedback.append("Password must be at least 8 characters")
    elif len(password) >= 12:
        score += 1
        feedback.append("Good length")
    else:
        score += 0.5

    # Uppercase check
    if requirements['uppercase']:
        score += 1
    else:
        feedback.append("Add uppercase letters")

    # Lowercase check
    if requirements['lowercase']:
        score += 1
    else:
        feedback.append("Add lowercase letters")

    # Number check
    if requirements['number']:
        score += 1
    else:
        feedback.append("Add numbers")

    # Special character check
    if requirements['special']:
        score += 1
    else:
        feedback.append("Add special characters (!@#$%^&*)")

    # Determine strength level
    score = int(score)
    if score == 0:
        strength = 'very_weak'
    elif score == 1:
        strength = 'weak'
    elif score == 2:
        strength = 'fair'
    elif score == 3:
        strength = 'good'
    else:  # score == 4
        strength = 'very_strong'

    # Add positive feedback if all requirements met
    if all(requirements.values()):
        feedback = ["Strong password!"] if len(feedback) == 0 else feedback

    return {
        'score': score,
        'strength': strength,
        'feedback': feedback,
        'requirements': requirements,
        'is_valid': all(requirements.values()) and len(password) >= 8
    }


def get_strength_color(strength: str) -> str:
    """Get color for password strength indicator.

    Args:
        strength: Strength level ('very_weak', 'weak', 'fair', 'good', 'very_strong')

    Returns:
        Tailwind CSS color class
    """
    colors = {
        'very_weak': 'bg-red-500',
        'weak': 'bg-orange-500',
        'fair': 'bg-yellow-500',
        'good': 'bg-blue-500',
        'very_strong': 'bg-green-500',
    }
    return colors.get(strength, 'bg-gray-500')


def get_strength_label(strength: str) -> str:
    """Get human-readable label for password strength.

    Args:
        strength: Strength level

    Returns:
        Label string
    """
    labels = {
        'very_weak': 'Very Weak',
        'weak': 'Weak',
        'fair': 'Fair',
        'good': 'Good',
        'very_strong': 'Very Strong',
    }
    return labels.get(strength, 'Unknown')
