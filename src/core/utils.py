"""
Utilitaires partagés pour l'ensemble du projet ECWM Challenge
"""
import os
import re
import unicodedata
from typing import Optional


def normalize_name(name: str) -> str:
    """
    Normalise un nom pour la comparaison (coureurs, courses, etc.)

    Transformations appliquées :
    - Conversion en majuscules
    - Suppression des accents (normalisation NFD)
    - Remplacement des tirets et apostrophes par des espaces
    - Normalisation des espaces multiples

    Args:
        name: Nom à normaliser

    Returns:
        Nom normalisé (ex: "François-Xavier O'Brien" → "FRANCOIS XAVIER O BRIEN")

    Examples:
        >>> normalize_name("François-Xavier")
        'FRANCOIS XAVIER'
        >>> normalize_name("O'Brien")
        'O BRIEN'
    """
    # Convertir en majuscules
    name = name.upper()

    # Supprimer les accents via décomposition NFD
    name = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'  # Mn = Nonspacing_Mark (accents)
    )

    # Remplacer tirets et apostrophes par des espaces
    name = name.replace('-', ' ').replace("'", " ")

    # Normaliser les espaces multiples
    name = ' '.join(name.split())

    return name.strip()


def normalize_name_strict(name: str) -> str:
    """
    Normalisation stricte : supprime tous les espaces et tirets

    Utilisé pour les comparaisons très permissives quand normalize_name() échoue.

    Args:
        name: Nom à normaliser

    Returns:
        Nom normalisé sans espaces (ex: "François-Xavier" → "FRANCOISXAVIER")

    Examples:
        >>> normalize_name_strict("François-Xavier O'Brien")
        'FRANCOISXAVIEROBRIEN'
    """
    name = normalize_name(name)
    # Supprimer tous les espaces et tirets
    return name.replace(' ', '').replace('-', '')


def extract_course_name(filename: str) -> str:
    """
    Extrait le nom de la course depuis un nom de fichier PDF

    Retire l'extension .pdf et le préfixe numérique optionnel (format: NN_nom.pdf)

    Args:
        filename: Nom du fichier (ex: "09_halluin.pdf")

    Returns:
        Nom de la course en minuscules (ex: "halluin")

    Examples:
        >>> extract_course_name("09_halluin.pdf")
        'halluin'
        >>> extract_course_name("verlinghem.pdf")
        'verlinghem'
    """
    # Retirer l'extension
    name = os.path.splitext(filename)[0]

    # Retirer le préfixe numérique optionnel (ex: "09_")
    name = re.sub(r'^\d+_', '', name)

    return name.lower()


def format_position(position: str) -> str:
    """
    Formate une position pour affichage

    Args:
        position: Position brute (ex: "1", "AB", "DNF")

    Returns:
        Position formatée avec suffixe ordinal si applicable

    Examples:
        >>> format_position("1")
        '1er'
        >>> format_position("3")
        '3e'
        >>> format_position("AB")
        'AB'
    """
    if position.isdigit():
        pos_int = int(position)
        if pos_int == 1:
            return "1er"
        else:
            return f"{pos_int}e"
    return position


def safe_float(value: Optional[str], default: float = 0.0) -> float:
    """
    Convertit une chaîne en float de manière sûre

    Args:
        value: Valeur à convertir
        default: Valeur par défaut si conversion échoue

    Returns:
        Float ou valeur par défaut

    Examples:
        >>> safe_float("3.14")
        3.14
        >>> safe_float("invalid", default=0.0)
        0.0
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Optional[str], default: int = 0) -> int:
    """
    Convertit une chaîne en int de manière sûre

    Args:
        value: Valeur à convertir
        default: Valeur par défaut si conversion échoue

    Returns:
        Integer ou valeur par défaut

    Examples:
        >>> safe_int("42")
        42
        >>> safe_int("invalid", default=0)
        0
    """
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default
