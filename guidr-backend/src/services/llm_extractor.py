"""LLM-powered (or heuristic) extraction pipeline."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.config import settings

try:
    from groq import AsyncGroq  # type: ignore
except Exception:  # pragma: no cover
    AsyncGroq = None  # type: ignore

try:
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore


class ProgramExtraction(BaseModel):
    name: Optional[str] = None
    degree_level: Optional[str] = None
    field_of_study: Optional[str] = None
    description: Optional[str] = None
    deadline_primary: Optional[str] = Field(default=None, alias="application_deadline_primary")
    tuition: Optional[float] = None
    requirements: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0


class InstitutionExtraction(BaseModel):
    name: Optional[str]
    city: Optional[str]
    state_or_province: Optional[str]
    country: Optional[str]
    website_url: Optional[str]
    institution_type: Optional[str]
    public_private: Optional[str]
    confidence_score: float = 0.0


class ProfessorExtraction(BaseModel):
    name: Optional[str]
    title: Optional[str]
    email: Optional[str]
    research_interests: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class LLMExtractor:
    """Coordinates Groq/OpenAI extraction with graceful fallbacks."""

    def __init__(self) -> None:
        self._groq = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key and AsyncGroq else None
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and AsyncOpenAI else None
        self._llm_enabled = settings.enable_llm_extraction and (self._groq or self._openai)

    async def extract_program_data(self, html_content: str, url: str) -> Dict[str, Any]:
        if self._llm_enabled:
            try:
                return await self._call_llm(
                    prompt="Extract graduate program details.",
                    html=html_content,
                    schema=ProgramExtraction,
                )
            except Exception:
                pass
        return self._fallback_program(html_content)

    async def extract_institution_data(self, html_content: str) -> Dict[str, Any]:
        if self._llm_enabled:
            try:
                return await self._call_llm(
                    prompt="Extract university or institution information.",
                    html=html_content,
                    schema=InstitutionExtraction,
                )
            except Exception:
                pass
        return self._fallback_institution(html_content)

    async def extract_professor_data(self, html_content: str) -> Dict[str, Any]:
        if self._llm_enabled:
            try:
                return await self._call_llm(
                    prompt="Extract professor or research mentor information.",
                    html=html_content,
                    schema=ProfessorExtraction,
                )
            except Exception:
                pass
        return self._fallback_professor(html_content)

    async def _call_llm(self, prompt: str, html: str, schema: type[BaseModel]) -> Dict[str, Any]:
        # Build schema hint for the prompt
        schema_fields = list(schema.model_fields.keys())
        schema_hint = ", ".join(schema_fields)
        
        # Limit HTML content to avoid token limits
        # Most models have context limits, so we'll use a conservative limit
        max_html_length = 4000  # Reduced from 6000 to avoid token limits
        html_truncated = html[:max_html_length]
        if len(html) > max_html_length:
            html_truncated += "\n\n[Content truncated...]"
        
        # Create a more concise system message
        system_message = f"Extract data and return ONLY valid JSON with these fields: {schema_hint}. No markdown, no explanation, just JSON."
        user_message = f"{prompt}\n\nExtract from this HTML and return JSON only:\n\n{html_truncated}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
        
        try:
            if self._groq:
                # Groq models may have different parameter support
                # Try with minimal parameters first
                try:
                    response = await self._groq.chat.completions.create(
                        model=settings.llm_extraction_model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1000,  # Limit response length
                    )
                    content = response.choices[0].message.content or "{}"
                except Exception as groq_error:
                    # If that fails, try with even more minimal parameters
                    logger.warning(f"Groq API error (first attempt): {groq_error}. Trying with minimal parameters...")
                    try:
                        response = await self._groq.chat.completions.create(
                            model=settings.llm_extraction_model,
                            messages=messages,
                        )
                        content = response.choices[0].message.content or "{}"
                    except Exception as groq_error2:
                        logger.error(f"Groq API error (second attempt): {groq_error2}")
                        raise groq_error2
                        
            elif self._openai:
                response = await self._openai.chat.completions.create(
                    model=settings.llm_extraction_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
            else:
                raise RuntimeError("LLM provider not configured.")
            
            # Clean up response - extract JSON if wrapped in markdown
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code blocks
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            
            # Try to extract JSON if it's embedded in text
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            # Validate and parse JSON
            try:
                parsed = schema.model_validate_json(content)
                return parsed.model_dump(by_alias=True)
            except Exception as parse_error:
                logger.warning(f"Failed to parse LLM response as JSON: {parse_error}. Content: {content[:200]}")
                # Return empty dict instead of failing
                return {}
                
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            # Return empty dict to allow fallback
            return {}

    def _fallback_program(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        paragraphs = " ".join(p.get_text(strip=True) for p in soup.find_all("p")[:3])
        return ProgramExtraction(
            name=title.get_text(strip=True) if title else None,
            degree_level=None,
            field_of_study=None,
            description=paragraphs or None,
            tuition=None,
            requirements={},
            confidence_score=0.2,
        ).model_dump(by_alias=True)

    def _fallback_institution(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        return InstitutionExtraction(
            name=title.get_text(strip=True) if title else None,
            confidence_score=0.2,
        ).model_dump()

    def _fallback_professor(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        name = soup.find("h1")
        return ProfessorExtraction(
            name=name.get_text(strip=True) if name else None,
            confidence_score=0.2,
        ).model_dump()


# Convenience singleton for synchronous contexts
def extract_program_sync(html_content: str, url: str) -> Dict[str, Any]:
    extractor = LLMExtractor()
    return asyncio.get_event_loop().run_until_complete(
        extractor.extract_program_data(html_content=html_content, url=url)
    )

