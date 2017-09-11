import re, sys, itertools, sqlite3

sqlite_file = "newwords.sqlite"


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_file = sys.argv[1]
    else:
        print ("Invalid syntax - merger.py dictionary.txt")
        exit()
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    c.execute("CREATE TABLE words (merged STRING NOT NULL, same STRING NOT NULL, pronunciation STRING NOT NULL, word STRING NOT NULL)")
    lines = [line.strip() for line in open(input_file)]
    for line in lines:
        word_info = line.split("  ")
        full_pronunciation = re.sub('[0-9]*',"", word_info[1])
        pronunciation = full_pronunciation.split(" ")
        if len(pronunciation) < 20:
            permutations = itertools.product([True, False], repeat=len(pronunciation))
            for possibility in permutations:
                new_pronunciation = pronunciation[:]
                reverse_pronunciation = pronunciation[:]
                for a in range(len(pronunciation)):
                    if possibility[a]:
                        new_pronunciation[a] = "."
                    else:
                        reverse_pronunciation[a] = "."
                reverse_word = " ".join(reverse_pronunciation)
                new_word = " ".join(new_pronunciation)
                final_word = re.sub("\. (?=\.)", "", new_word)
                final_reverse = re.sub("\. (?=\.)", "", reverse_word)
                c.execute("INSERT OR IGNORE INTO words (merged, same, pronunciation, word) VALUES (?, ?, ?, ?)", (final_word, final_reverse, full_pronunciation, word_info[0]))
            conn.commit()
            print ("Processed "+word_info[0])
    conn.close()
    exit()