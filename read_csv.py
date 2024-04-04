import csv

def readCSVHarpa(indice):
    with open('listaharpa.csv', newline='') as csvfile:
        spamreader = list(csv.reader(csvfile, delimiter=';', quotechar='|'))
        return spamreader[indice - 1][0][11:]