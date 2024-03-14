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

    collection_name = ".".join([config.namespace, "options"])

    @classmethod
    def test_mongo(cls):
        print(f"Returns estimated document count for {cls.collection_name} collection")
        return cls(config.mongo_db()).db[cls.collection_name].estimated_document_count()

    @classmethod
    def get_all(cls, **filters):
        return cls().find(filters)

    def __init__(self, database=None):
        self.db = database if database is not None else config.mongo_db()
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
