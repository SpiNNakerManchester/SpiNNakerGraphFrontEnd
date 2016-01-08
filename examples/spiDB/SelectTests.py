__author__ = 'gmtuca'

import unittest

from spiDB_socket_connection import SpiDBSocketConnection

conn = SpiDBSocketConnection()

def assertSelectValid(testCase, result, expected_n_rows, expected_n_cols):

    testCase.assertIsNotNone(result)
    testCase.assertIsNotNone(result.rows)
    testCase.assertEqual(len(result.rows), expected_n_rows)

    if expected_n_rows > 0:
        first_row = result.rows.itervalues().next()
        testCase.assertEqual(len(first_row), expected_n_cols)

class TestSimpleStringTable(unittest.TestCase):

    def setUp(self):
        c = """CREATE TABLE People(
               name varchar(20),
               middlename varchar(20),
               lastname varchar(20)
               );
            """

        i = """INSERT INTO People(
            name,middlename,lastname)
            VALUES (Tuca,Bicalho,Ceccotti);
            """

        self.createResult = conn.run([c])[0]
        self.insertResult = conn.run([i])[0]

    def test_select_single_entry_which_is_there0(self):
        s = "SELECT * FROM People WHERE middlename = 'Bicalho';"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=1,
                          expected_n_cols=3)

        first_row = selectResult.rows.itervalues().next()
        self.assertEqual(first_row,
                         {"name":"Tuca",
                          "middlename" :"Bicalho",
                          "lastname" : "Ceccotti"})

    def test_select_single_entry_which_is_there1(self):
        s = "SELECT * FROM People;"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=1,
                          expected_n_cols=3)
        first_row = selectResult.rows.itervalues().next()
        self.assertEqual(first_row,
                 {"name":"Tuca",
                  "middlename" :"Bicalho",
                  "lastname" : "Ceccotti"})

    def test_single_entry_which_is_not_there(self):
        s = "SELECT * FROM People WHERE middlename = 'Lester';"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=0,
                          expected_n_cols=0)

class TestSingleEntryTable(unittest.TestCase):

    def setUp(self):
        self.createResult = conn.run(["CREATE TABLE Dog(breed varchar(35));"])[0]

        self.breeds = [ "Labrador Retriever",
                        "Beagle",
                        "English Cocker Spaniel",
                        "English Springer Spaniel",
                        "German Shepherd",
                        "Poodle",
                        "Staffordshire Bull Terrier",
                        "Cavalier King Charles Spaniel",
                        "Golden Retriever",
                        "West Highland White Terrier",
                        "Boxer",
                        "Border Terrier",
                        "Pug"]

        inserts = []

        for b in self.breeds:
            inserts.append("INSERT INTO Dog(breed) VALUES ({});".format(b))

        self.insertResults = conn.run(inserts)

    def test_select_all_entries(self):
        s = "SELECT * FROM Dog;"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=len(self.breeds),
                          expected_n_cols=1)

        rows = selectResult.rows.values()

        values = set()
        for r in rows:
            (k,v) = r.iteritems().next()
            values.add(v)

        for b in self.breeds:
            self.assertTrue(b in values, "{} is not in values".format(b))


if __name__ == '__main__':
    unittest.main()
