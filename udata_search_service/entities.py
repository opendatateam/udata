import dataclasses
from datetime import datetime

from dateutil.parser import isoparse


@dataclasses.dataclass
class EntityBase:
    @classmethod
    def load_from_dict(cls, data):
        fields = [f.name for f in dataclasses.fields(cls)]
        data = {key: data[key] for key in data if key in fields}
        return cls(**data)

    def to_dict(self):
        # Manual conversion instead of dataclasses.asdict() because asdict() tries to
        # reconstruct list-like types (e.g. MongoEngine BaseList) which fails.
        result = {}
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if isinstance(value, list):
                value = list(value)
            result[f.name] = value
        return result


@dataclasses.dataclass
class Organization(EntityBase):
    id: str
    name: str
    description: str
    url: str
    orga_sp: int
    created_at: datetime.date
    followers: int
    datasets: int
    views: int
    reuses: int

    badges: list[str] = None
    producer_type: list[str] = None
    acronym: str = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)


@dataclasses.dataclass
class Dataset(EntityBase):
    id: str
    title: str
    url: str
    created_at: datetime.date
    frequency: str
    format: list[str]
    views: int
    followers: int
    reuses: int
    featured: int
    resources_count: int
    concat_title_org: str
    description: str

    last_update: datetime.date = None
    acronym: str = None
    badges: list[str] = None
    tags: list[str] = None
    license: str = None
    temporal_coverage_start: datetime.date = None
    temporal_coverage_end: datetime.date = None
    granularity: str = None
    geozones: list[str] = None
    schema: list[str] = None
    topics: list[str] = None
    resources_ids: list[str] = None
    resources_titles: list[str] = None

    orga_sp: int = None
    orga_followers: int = None
    organization: str = None
    organization_name: str = None
    organization_badges: list[str] = None
    owner: str = None
    access_type: str = None
    format_family: list[str] = None
    producer_type: list[str] = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.last_update, str):
            self.last_update = isoparse(self.last_update)
        if isinstance(self.temporal_coverage_start, str):
            self.temporal_coverage_start = isoparse(self.temporal_coverage_start)
        if isinstance(self.temporal_coverage_end, str):
            self.temporal_coverage_end = isoparse(self.temporal_coverage_end)


@dataclasses.dataclass
class Reuse(EntityBase):
    id: str
    title: str
    url: str
    created_at: datetime.date
    views: int
    followers: int
    datasets: int
    featured: int
    description: str
    type: str
    topic: str

    last_modified: datetime.date = None
    archived: datetime.date = None
    tags: list[str] = None
    badges: list[str] = None
    topic_object: list[str] = None
    orga_followers: int = None
    organization: str = None
    organization_name: str = None
    organization_badges: list[str] = None
    owner: str = None
    producer_type: list[str] = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.last_modified, str):
            self.last_modified = isoparse(self.last_modified)
        if isinstance(self.archived, str):
            self.archived = isoparse(self.archived)


@dataclasses.dataclass
class Dataservice(EntityBase):
    id: str
    title: str
    description: str
    description_length: float
    created_at: datetime.date
    metadata_modified_at: datetime.date = None

    views: int = 0
    followers: int = 0
    is_restricted: bool = None
    orga_followers: int = None
    organization: str = None
    organization_name: str = None
    owner: str = None
    tags: list[str] = None
    topics: list[str] = None
    access_type: str = None
    producer_type: list[str] = None
    documentation_content: str = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.metadata_modified_at, str):
            self.metadata_modified_at = isoparse(self.metadata_modified_at)


@dataclasses.dataclass
class Topic(EntityBase):
    id: str
    name: str
    description: str
    created_at: datetime.date

    tags: list[str] = None
    featured: bool = False
    private: bool = False
    last_modified: datetime.date = None
    organization: str = None
    organization_name: str = None
    producer_type: list[str] = None
    nb_datasets: int = 0
    nb_reuses: int = 0
    nb_dataservices: int = 0
    elements_titles: list[str] = None
    elements_descriptions: list[str] = None
    elements_tags: list[str] = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.last_modified, str):
            self.last_modified = isoparse(self.last_modified)


@dataclasses.dataclass
class Discussion(EntityBase):
    id: str
    title: str
    content: str = None
    created_at: datetime.date = None
    closed_at: datetime.date = None
    closed: bool = False
    subject_class: str = None
    subject_id: str = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.closed_at, str):
            self.closed_at = isoparse(self.closed_at)


@dataclasses.dataclass
class Post(EntityBase):
    id: str
    name: str
    headline: str = None
    content: str = None
    tags: list[str] = None
    created_at: datetime.date = None
    last_modified: datetime.date = None
    published: datetime.date = None

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = isoparse(self.created_at)
        if isinstance(self.last_modified, str):
            self.last_modified = isoparse(self.last_modified)
        if isinstance(self.published, str):
            self.published = isoparse(self.published)
