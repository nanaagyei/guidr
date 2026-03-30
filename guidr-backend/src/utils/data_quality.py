"""Data quality metrics tracking for scraped data."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics for a single extraction attempt."""
    method: str  # 'firecrawl', 'llm_agent', 'playwright', etc.
    success: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    fields_extracted: int = 0
    total_fields: int = 0


@dataclass
class DataQualityMetrics:
    """Overall data quality metrics."""
    extraction_success_rate: Dict[str, float] = field(default_factory=dict)  # method -> success rate
    completeness_scores: List[int] = field(default_factory=list)
    validation_failures: Dict[str, int] = field(default_factory=dict)  # reason -> count
    missing_field_patterns: Dict[str, int] = field(default_factory=dict)  # field -> count
    total_extractions: int = 0
    successful_extractions: int = 0


class DataQualityTracker:
    """Track data quality metrics for scraped data."""
    
    def __init__(self):
        self.metrics: List[ExtractionMetrics] = []
        self.quality_metrics = DataQualityMetrics()
    
    def record_extraction(
        self,
        method: str,
        success: bool,
        fields_extracted: int = 0,
        total_fields: int = 0,
        error_message: Optional[str] = None
    ):
        """Record an extraction attempt."""
        metric = ExtractionMetrics(
            method=method,
            success=success,
            fields_extracted=fields_extracted,
            total_fields=total_fields,
            error_message=error_message,
        )
        self.metrics.append(metric)
        self.quality_metrics.total_extractions += 1
        if success:
            self.quality_metrics.successful_extractions += 1
    
    def record_completeness_score(self, score: int):
        """Record a completeness score."""
        self.quality_metrics.completeness_scores.append(score)
    
    def record_validation_failure(self, reason: str):
        """Record a validation failure."""
        self.quality_metrics.validation_failures[reason] = (
            self.quality_metrics.validation_failures.get(reason, 0) + 1
        )
    
    def record_missing_field(self, field_name: str):
        """Record a missing field."""
        self.quality_metrics.missing_field_patterns[field_name] = (
            self.quality_metrics.missing_field_patterns.get(field_name, 0) + 1
        )
    
    def calculate_success_rates(self) -> Dict[str, float]:
        """Calculate success rates per extraction method."""
        method_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "total": 0})
        
        for metric in self.metrics:
            method_stats[metric.method]["total"] += 1
            if metric.success:
                method_stats[metric.method]["success"] += 1
        
        success_rates = {}
        for method, stats in method_stats.items():
            if stats["total"] > 0:
                success_rates[method] = stats["success"] / stats["total"]
        
        self.quality_metrics.extraction_success_rate = success_rates
        return success_rates
    
    def get_summary(self) -> Dict[str, any]:
        """Get summary of data quality metrics."""
        self.calculate_success_rates()
        
        avg_completeness = (
            sum(self.quality_metrics.completeness_scores) / len(self.quality_metrics.completeness_scores)
            if self.quality_metrics.completeness_scores else 0
        )
        
        overall_success_rate = (
            self.quality_metrics.successful_extractions / self.quality_metrics.total_extractions
            if self.quality_metrics.total_extractions > 0 else 0
        )
        
        return {
            "overall_success_rate": overall_success_rate,
            "method_success_rates": self.quality_metrics.extraction_success_rate,
            "average_completeness_score": avg_completeness,
            "total_extractions": self.quality_metrics.total_extractions,
            "successful_extractions": self.quality_metrics.successful_extractions,
            "validation_failures": dict(self.quality_metrics.validation_failures),
            "most_missing_fields": dict(
                sorted(
                    self.quality_metrics.missing_field_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ),
        }
    
    def reset(self):
        """Reset all metrics."""
        self.metrics = []
        self.quality_metrics = DataQualityMetrics()


# Global tracker instance
_global_tracker = DataQualityTracker()


def get_tracker() -> DataQualityTracker:
    """Get the global data quality tracker."""
    return _global_tracker

