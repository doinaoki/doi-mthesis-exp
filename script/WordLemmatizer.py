import nltk
from nltk.stem import WordNetLemmatizer 
from nltk.corpus import wordnet

nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

class WordLemmatizer:
    def __init__(self):
        self._wnl = WordNetLemmatizer()
        self._store = {}
        return

    # word: "word"
    def lemmatize(self, word):
        if word in self._store.keys():
            return self._store[word]
        else:
            # 単語のみを渡すために list へ変換
            _, tag = nltk.pos_tag([word])[0]
            lemmatized_word = self._wnl.lemmatize(word, pos=self._toPos(tag))
            self._store[word] = lemmatized_word
            return lemmatized_word

    # tag: "nltk.pos_tag result"
    def _toPos(self, tag):
        # from https://stackoverflow.com/questions/15586721/wordnet-lemmatization-and-pos-tagging-in-python
        # nltk の出力を WordNetLemmatizer に渡す pos に変換
        # （指定しないと正しく lemmatize されない）
        if tag.startswith('J'):
            return wordnet.ADJ
        elif tag.startswith('V'):
            return wordnet.VERB
        elif tag.startswith('N'):
            return wordnet.NOUN
        elif tag.startswith('R'):
            return wordnet.ADV
        else:
            # As default pos in lemmatization is Noun
            return wordnet.NOUN