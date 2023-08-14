from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_top_similar_n(base_texts: list, news: list, n_top: int) -> list:
    tv = TfidfVectorizer(max_features=1000, ngram_range=(3, 6), analyzer='char_wb')
    tv.fit(base_texts)

    base_vector = tv.transform([" ".join(base_texts)])
    dataset = tv.transform(news)

    distances = cosine_similarity(base_vector, dataset)[0]
    distances_and_i = zip(distances, range(len(news)))
    distances_and_i = sorted(distances_and_i, key=lambda d_i: -d_i[0])
    distances_and_i = distances_and_i[:n_top]

    return [d_i[1] for d_i in distances_and_i]
