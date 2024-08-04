
import os
from datetime import date
from mongoengine import (
        StringField,
        DateField,
        ListField,
        FloatField,
        DictField,
        DateTimeField,
        ReferenceField,
        IntField,
        Document
        
)

class MongoPatent(Document):

    patent_number = StringField(unique=True, required=True)
    pdf_url = ListField(StringField())
    priority_date = DateField()
    filing_date = DateField()
    publication_date = DateField()
    abstract = StringField()
    specification = StringField()
    claims = ListField(DictField())
    title = StringField()
    jurisdiction = StringField()
    inventors = ListField(StringField())
    assignees = ListField(StringField())
    status = StringField()
    classifications = StringField()
    images = ListField(StringField())

