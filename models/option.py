from config import config


class Option:
    """
    Persist option JSON data
    Since I'm kind of a nosql noob I'll push the
    fancy design pattern stuff to v2

    Assumes:
    1. MongoDB database
    2. API data is from HOOD
    """

    collection_name = "options"

    @classmethod
    def test_mongo(cls):
        print("Returns estimated document count for 'options' collection")
        return cls(config.mongo_db()).db.options.estimated_document_count()

    def __init__(self, database):
        self.db = database
        self.collection = self.db[self.collection_name]

    def validate_properties(self, docs):
        pass

    def create(self, docs):
        """
        inserts a dict or array of dicts
        """
        self.validate_properties(docs)

        if isinstance(docs, dict):
            return self.collection.insert_one(docs)
        return self.collection.insert_many(docs)

    def find(self, query=None):
        return list(self.collection.find(query))

    def update(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError
