import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


# Load dataset
df = pd.read_csv("ml/dataset/Symptom2Disease.csv")

# Remove exact duplicate symptom descriptions
df = df.drop_duplicates(subset="text").reset_index(drop=True)

X = df["text"]
y = df["label"]


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# Convert text into TF-IDF features
vectorizer = TfidfVectorizer()

X_train_tfidf = vectorizer.fit_transform(X_train)


# Train model
model = LogisticRegression(max_iter=1000)

model.fit(X_train_tfidf, y_train)


# Save trained model and vectorizer
joblib.dump(vectorizer, "ml/tfidf_vectorizer.pkl")
joblib.dump(model, "ml/symptom_model.pkl")

print("Model training completed successfully.")
print("Vectorizer saved: ml/tfidf_vectorizer.pkl")
print("Model saved: ml/symptom_model.pkl")