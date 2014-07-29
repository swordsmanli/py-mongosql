import unittest
from sqlalchemy import inspect

from . import models


class QueryTest(unittest.TestCase):
    """ Test MongoQuery """

    def setUp(self):
        # Connect, create tables
        engine, Session = models.init_database()
        models.drop_all(engine)
        models.create_all(engine)

        # Fill DB
        ssn = Session()
        ssn.begin()
        ssn.add_all(models.content_samples())
        ssn.commit()

        # Session
        self.engine = engine
        self.db = Session()

        # Logging
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    def tearDown(self):
        pass#models.drop_all(self.engine)  # FIXME: test hangs when dropping tables for the second time!

    def test_projection(self):
        ssn = self.db

        # Test: load only 2 props
        user = models.User.mongoquery(ssn).project(['id', 'name']).end().first()
        self.assertEqual(inspect(user).unloaded, {'age', 'tags', 'articles', 'comments'})

        # Test: load without 2 props
        user = models.User.mongoquery(ssn).project('-age,tags').end().first()
        self.assertEqual(inspect(user).unloaded, {'age', 'tags', 'articles', 'comments'})

    def test_sort(self):
        ssn = self.db

        # Test: sort(age+, id-)
        users = models.User.mongoquery(ssn).sort(['age+', 'id+']).end().all()
        self.assertEqual([3, 1, 2], [u.id for u in users])

    def test_filter(self):
        ssn = self.db

        # Test: filter(age=16)
        users = models.User.mongoquery(ssn).filter({'age': 16}).end().all()
        self.assertEqual([3], [u.id for u in users])

    def test_join(self):
        ssn = self.db

        # Test: no join(), relationships are unloaded
        user = models.User.mongoquery(ssn).end().first()
        self.assertEqual(inspect(user).unloaded, {'articles', 'comments'})

        # Test:    join(), relationships are   loaded
        user = models.User.mongoquery(ssn).join(['articles']).end().first()
        self.assertEqual(inspect(user).unloaded, {'comments'})

    def test_count(self):
        ssn = self.db

        # Test: count()
        n = models.User.mongoquery(ssn).count().end().scalar()
        self.assertEqual(3, n)

    def test_aggregate(self):
        ssn = self.db

        row2dict = lambda row: dict(zip(row.keys(), row))  # zip into a dict

        # Test: aggregate()
        q = {
            'max_age': {'$max': 'age'},
            'adults': {'$sum': {'age': {'$gte': 18}}},
        }
        row = models.User.mongoquery(ssn).aggregate(q).end().one()
        ':type row: sqlalchemy.util.KeyedTuple'
        self.assertEqual(row2dict(row), {'max_age': 18, 'adults': 2})

        # Test: aggregate { $sum: 1 }
        row = models.User.mongoquery(ssn).aggregate({ 'n': {'$sum': 1} }).end().one()
        self.assertEqual(row.n, 3)

        # Test: aggregate { $sum: 10 }
        row = models.User.mongoquery(ssn).aggregate({'n': {'$sum': 10}}).end().one()
        self.assertEqual(row.n, 30)

        # Test: aggregate() & group()
        q = {
            'age': 'age',
            'n': {'$sum': 1},
        }
        rows = models.User.mongoquery(ssn).aggregate(q).group(['age']).sort(['age-']).end().all()
        self.assertEqual(map(row2dict, rows), [ {'age': 18, 'n': 2}, {'age': 16, 'n': 1} ])