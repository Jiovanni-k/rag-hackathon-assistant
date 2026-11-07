"""Core data objects shared by every layer."""
from dataclasses import dataclass, field, asdict


@dataclass
class Chunk:
    id: str
    text: str              # what is embedded and searched (includes the context header)
    source: str            # file name
    title: str             # document title, e.g. "جامعة النجاح الوطنية — بكالوريوس القانون"
    section: str = ""      # e.g. "10. WITHDRAWAL" or "السنة الثانية - الفصل الأول"
    page: int = 0          # 0 when the format has no pages (.txt)

    def metadata(self):
        return {"source": self.source, "title": self.title, "section": self.section, "page": self.page}


@dataclass
class Hit:
    chunk: Chunk
    score: float = 0.0     # reranker score, higher is better
    distance: float = 1.0  # best vector distance, lower is better


@dataclass
class Source:
    document: str
    title: str
    page: int
    section: str
    snippet: str

    def label(self):
        where = f"صفحة {self.page}" if self.page else self.section
        return f"{self.document}، {where}" if where else self.document


@dataclass
class Answer:
    text: str
    sources: list = field(default_factory=list)   # list[Source]
    refused: bool = False
    reason: str = "answered"   # answered | not_found | out_of_scope | llm_unavailable
    standalone_question: str = ""
    # Debug info for evaluation and logs (not shown to students)
    retrieved: list = field(default_factory=list)   # chunk texts given to / considered for the LLM
    best_distance: float = 1.0

    def to_dict(self, debug=False):
        data = asdict(self)
        if not debug:
            data.pop("retrieved")
            data.pop("best_distance")
        return data
