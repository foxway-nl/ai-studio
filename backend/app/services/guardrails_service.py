"""Guardrails & Kindveiligheid Service voor AI-Studio.

Valideert scripts, beeldprompts, audio en YouTube-metadata tegen strikte
regels voor kinderen tot 7 jaar (geen geweld, geen angstaanjagende thema's,
positieve pedagogische boodschap).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Verboden woorden / gevaarlijke thema's voor jonge peuters/kleuters
_UNSAFE_PATTERNS = [
    r"\b(dood|doodgaan|vermoord|bloed|mes|pistool|wapen|vechten|slaan|sterven)\b",
    r"\b(monster|spook|duivel|hel|nachtmerrie|griezelig|eng|angst|duister|engerd)\b",
    r"\b(seks|naakt|bier|wijn|alcohol|roken|sigaret|drugs)\b",
    r"\b(haat|lelijk|stommerik|idioot|domkop|sukkel)\b",
    r"\b(kill|blood|weapon|gun|knife|fight|die|death|scary|dark|horror)\b",
]

# Positieve educatieve markers (bevordert hogere score)
_EDUCATIONAL_PATTERNS = [
    r"\b(leren|tellen|kleur|kleuren|delen|vriendje|vriendjes|samen|helpen)\b",
    r"\b(goed zo|knap|probeer|zing|liedje|vrolijk|ontdekken|waarom|hoe)\b",
]


class GuardrailsService:
    """Valideert content voor veilige educatieve YouTube Kids publicatie."""

    def validate_script(
        self,
        script: str,
        target_age_min: int = 3,
        target_age_max: int = 7,
    ) -> Dict[str, Any]:
        """Valideer een volledig script op kindveiligheid en pedagogische kwaliteit."""
        issues: List[str] = []
        lower_script = script.lower()

        # Check verboden termen
        for pat in _UNSAFE_PATTERNS:
            matches = re.findall(pat, lower_script, re.IGNORECASE)
            if matches:
                issues.append(f"Onveilige/enge woorden ontdekt: {', '.join(set(matches))}")

        # Check educatieve waarde
        edu_matches = sum(len(re.findall(pat, lower_script, re.IGNORECASE)) for pat in _EDUCATIONAL_PATTERNS)
        if edu_matches == 0:
            issues.append("Het script bevat weinig interactieve of educatieve triggers.")

        # Check zinslengte (kleuters begrijpen zinnen > 18 woorden minder goed)
        sentences = [s.strip() for s in re.split(r"[.!?]", script) if s.strip()]
        long_sentences = [s for s in sentences if len(s.split()) > 20]
        if len(long_sentences) > 3:
            issues.append("Enkele zinnen zijn te lang of complex voor jonge kinderen.")

        is_safe = len([i for i in issues if "Onveilig" in i]) == 0
        score = max(0, min(100, 100 - (len(issues) * 15) + min(15, edu_matches * 3)))

        return {
            "passed": is_safe,
            "safety_score": score,
            "issues": issues,
            "target_age": f"{target_age_min}-{target_age_max} jaar",
        }

    def validate_image_prompt(self, prompt: str) -> Dict[str, Any]:
        """Controleer een beeldprompt op ongeschikte termen."""
        issues = []
        lower = prompt.lower()
        for pat in _UNSAFE_PATTERNS:
            m = re.findall(pat, lower, re.IGNORECASE)
            if m:
                issues.append(f"Prompt bevat ongeschikte visuele termen: {', '.join(set(m))}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "safe_prompt": prompt if len(issues) == 0 else re.sub(r"|".join(_UNSAFE_PATTERNS), "", prompt),
        }

    def validate_audio_content(self, text: str) -> Dict[str, Any]:
        """Controleer gesproken tekst voor TTS."""
        return self.validate_script(text)

    def validate_seo_content(
        self,
        title: str,
        description: str,
        tags: List[str],
    ) -> Dict[str, Any]:
        """Controleer YouTube SEO metadata voor YouTube Kids richtlijnen."""
        issues = []
        combined = f"{title} {description} {' '.join(tags)}".lower()

        for pat in _UNSAFE_PATTERNS:
            m = re.findall(pat, combined, re.IGNORECASE)
            if m:
                issues.append(f"SEO metadata bevat ongepaste termen: {', '.join(set(m))}")

        # Check YouTube MadeForKids regel: geen misleidende clickbait
        if "gratis geld" in combined or "vbucks" in combined or "iphone" in combined:
            issues.append("Commerciële clickbait mag niet in kinder-content voorkomen.")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    def get_content_rating(self, script: str) -> Dict[str, Any]:
        """Genereer een kindvriendelijkheidsrapport met score."""
        val = self.validate_script(script)
        rating_label = "AL (Alle Leeftijden)" if val["safety_score"] >= 80 else "Aanpassen vereist"
        return {
            "rating": rating_label,
            "score": val["safety_score"],
            "passed": val["passed"],
            "recommendations": val["issues"],
        }

    # ─────────────────────────────────────────────────────────────
    # Scène- en afleveringsniveau (Viral Coach / Guardrails)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get(item: Any, key: str, default: Any = "") -> Any:
        """Lees een veld van een SQLModel-object of dictionary."""
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    def evaluate_scene(self, scene: Any) -> List[str]:
        """Geef concrete waarschuwingen voor één scène."""
        warnings: List[str] = []
        text = (self._get(scene, "narration_text", "") or "").strip()
        duration = float(self._get(scene, "duration_seconds", 8.0) or 8.0)
        animation = str(self._get(scene, "animation_type", "ken_burns") or "ken_burns")
        transition = str(self._get(scene, "transition_type", "crossfade") or "crossfade")

        if text:
            # Kindveiligheid
            for pat in _UNSAFE_PATTERNS:
                matches = re.findall(pat, text, re.IGNORECASE)
                if matches:
                    warnings.append(
                        f"Onveilige/enge woorden: {', '.join(sorted(set(matches)))}"
                    )
                    break

            # Te lange zinnen (>15 woorden volgens specificatie)
            sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
            long_sentences = [s for s in sentences if len(s.split()) > 15]
            if long_sentences:
                warnings.append(
                    f"{len(long_sentences)} zin(nen) bevatten meer dan 15 woorden; "
                    "houd zinnen kort en beeldend."
                )

            # Interactie / verhaallijn
            if not re.search(r"\?", text):
                relation = str(self._get(scene, "chapter_type", "") or "")
                if relation in ("question",):
                    warnings.append("Kijkersvraag bevat geen vraagteken.")

        # Visuele stilstand
        if duration > 7.0 and animation in ("static", "none"):
            warnings.append(
                f"Scène duurt {duration:.0f}s zonder camerabeweging; "
                "splits de scène of voeg beweging toe voor jonge kijkers."
            )

        # Overgang naar volgende scène
        if transition in ("static", "none", ""):
            warnings.append("Geen overgang gekozen; gebruik een harde cut of dissolve.")

        return warnings

    def evaluate_episode(
        self,
        scenes: List[Any],
        target_duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Genereer een volledig guardrails-rapport voor een aflevering."""
        issues: List[Dict[str, Any]] = []
        total_duration = 0.0
        last_interaction_at = 0.0
        current_time = 0.0
        safety_score = 100

        for idx, scene in enumerate(scenes):
            scene_id = self._get(scene, "id", None)
            scene_number = int(self._get(scene, "scene_number", idx + 1) or idx + 1)
            duration = float(self._get(scene, "duration_seconds", 0.0) or 0.0)
            total_duration += duration
            current_time += duration

            scene_warnings = self.evaluate_scene(scene)
            for warning in scene_warnings:
                level = "error" if "Onveilige" in warning else "warning"
                if level == "error":
                    safety_score -= 25
                else:
                    safety_score -= 3
                issues.append(
                    {
                        "level": level,
                        "message": warning,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                    }
                )

            chapter = str(self._get(scene, "chapter_type", "") or "")
            text = str(self._get(scene, "narration_text", "") or "")
            if chapter == "question" or "?" in text:
                last_interaction_at = current_time
            elif current_time - last_interaction_at > 180:
                issues.append(
                    {
                        "level": "warning",
                        "message": "Meer dan 3 minuten zonder interactie of kijkersvraag.",
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                    }
                )
                last_interaction_at = current_time

        # Totale duur (8–16 minuten)
        if scenes:
            if total_duration < 8 * 60:
                issues.append(
                    {
                        "level": "warning",
                        "message": (
                            f"Totale duur is {total_duration / 60:.1f} min; "
                            "streef naar 8–16 minuten."
                        ),
                    }
                )
            elif total_duration > 16 * 60:
                issues.append(
                    {
                        "level": "warning",
                        "message": (
                            f"Totale duur is {total_duration / 60:.1f} min; "
                            "de doelgroep raakt na 16 minuten afgeleid."
                        ),
                    }
                )

        if not scenes:
            safety_score = 0
            issues.append(
                {
                    "level": "warning",
                    "message": "De aflevering bevat nog geen scènes.",
                }
            )

        return {
            "passed": not any(issue["level"] == "error" for issue in issues),
            "safety_score": max(0, min(100, safety_score)),
            "total_duration_seconds": round(total_duration, 2),
            "scene_count": len(scenes),
            "issues": issues,
        }


guardrails_service = GuardrailsService()

