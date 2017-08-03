
import string
import random
from random import randint
import requests

word_site = "http://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain"

response = requests.get(word_site)
WORDS = response.content.splitlines()

WORDS_4_to_10char = []

for w in WORDS:
	if len(w) >= 4 and len(w) <= 10:
		WORDS_4_to_10char.append(w)

def roulette():
	return random.randint(0,1) is 1

def randomInteger():
	return random.randint(1,100000)

def randomWord():
	w = random.choice(WORDS_4_to_10char)
	if '\'' in w or '.' in w:
		return randomWord()
	return w

def randomString(N):
	return ''.join(random.choice(string.ascii_uppercase) for _ in range(N))

lines = 1000

puts = []
pulls = []

for i in range(lines):
	r1 = randomWord() if roulette() else randomInteger()
	r2 = randomWord() if roulette() else randomInteger()

	puts.append((r1, r2))

for i in range(lines):
	pulls.append(random.choice(puts)[0])

f = open('put_{}.kv'.format(lines),'w')
for k, v in puts:
	f.write('put {} {}\n'.format(k, v))
f.close()

f = open('pull_{}.kv'.format(lines),'w')
for k in pulls:
	f.write('pull {}\n'.format(k))
f.close()

f.close()