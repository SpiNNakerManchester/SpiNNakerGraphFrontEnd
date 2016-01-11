__author__ = 'gmtuca'

import unittest
import random

from spiDB_socket_connection import SpiDBSocketConnection

conn = SpiDBSocketConnection()

def assertSelectValid(testCase, result, expected_n_rows, expected_n_cols):

    testCase.assertIsNotNone(result)
    testCase.assertIsNotNone(result.rowidToRow)
    testCase.assertEqual(len(result.rowidToRow), expected_n_rows)

    if expected_n_rows > 0:
        first_row = result.rowidToRow.itervalues().next()
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

        first_row = selectResult.rowidToRow.itervalues().next()
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
        first_row = selectResult.rowidToRow.itervalues().next()
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

        rows = selectResult.getRows()

        values = set()
        for r in rows:
            (k,v) = r.iteritems().next()
            values.add(v)

        for b in self.breeds:
            self.assertTrue(b in values, "{} is not in values".format(b))


names = [     "Elmira","Leeanna","Dewey","Jerrod","Riva","Melynda",
              "Howard","Ahmad","Sadie","Rosaline","Gianna","Darcie",
              "Anamaria","Anya","Michael","Patrice","Georgina","Paul",
              "Lara","Jenelle","Hiroko","Burl","Angle","Darell","Lynne",
              "Penni","Latosha","Sherman","Ching","Maya","Alysia"]

last_names = [     "Hoobler","Soule","Cooter","Pavlak","Albee",
                   "Alvelo","Carlow","Anwar","Lester","Flavell",
                   "Douglass","Hilt","Beresford","Wolfe","Wooton",
                   "Smith","Johnson","Mooneyhan","Cole","Young",
                   "Dickson","Lisby","Daly","Halter","Blasi","Soden",
                   "Ceccotti","Dulaney","Hermes","Perri","Branner",
                   "Mascio","Chappelle","Lindbloom"]

addresses = [    "89 Oak Street - Lynchburg VA",
                 "670 Wall Street - Jersey City NJ",
                 "537 Lincoln Street - Rosemount MN",
                 "61 Route 64 - Wadsworth OH",
                 "184 Franklin Street - Warwick RI",
                 "985 Wood Street - Opa Locka FL",
                 "739 William Street - Southgate MI",
                 "46 Euclid Avenue - North Fort Myers FL",
                 "459 Harrison Avenue - Sun Prairie WI",
                 "126 King Street - Collegeville PA",
                 "279 Division Street - Billerica MA",
                 "396 Garden Street - Wheeling WV"]

class TestMultipleTypesAndSizesTable(unittest.TestCase):

    def setUp(self):
        c = """CREATE TABLE Person(
                name     varchar(20),
                lastname varchar(30),
                gender   varchar(1),
                address  varchar(50)
                );
            """
        #age      integer,
        #nin      integer

        self.createResult = conn.run([c])[0]

        self.number_of_people = 10

        inserts = []
        for i in range(self.number_of_people):
            inserts.append("INSERT INTO Person("
                           "name,lastname,gender,address"
                           ") VALUES ("
                           "{},{},{},{});"
                           .format(random.choice(names),
                                   random.choice(last_names),
                                   random.choice(['M','F']),
                                   random.choice(addresses)))

        self.insertResults = conn.run(inserts)

    def test_select_all_entries(self):
        s = "SELECT * FROM Person;"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=self.number_of_people,
                          expected_n_cols=4)

        rows = selectResult.getRows()

        for r in rows:
            self.assertIn(r["name"], names)
            self.assertIn(r["lastname"], last_names)
            self.assertIn(r["address"], addresses)
            self.assertIn(r["gender"], ['M','F'])

    def test_select_one_entry(self):
        s = "SELECT name FROM Person;"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=self.number_of_people,
                          expected_n_cols=1)

        for r in selectResult.getRows(): self.assertIn(r["name"], names)

    def test_select_two_entries(self):
        s = "SELECT name, lastname FROM Person;"
        selectResult = conn.run([s])[0]

        print "{}\n{}".format(s,selectResult)

        assertSelectValid(testCase=self,
                          result=selectResult,
                          expected_n_rows=self.number_of_people,
                          expected_n_cols=2)

        for r in selectResult.getRows():
            self.assertIn(r["name"], names)
            self.assertIn(r["lastname"], last_names)

if __name__ == '__main__':
    unittest.main()
