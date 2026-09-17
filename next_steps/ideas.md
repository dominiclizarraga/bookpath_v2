1. Me gustaría saber si podemos entrenar un Small language model (con lora) como parte de los experimentos y evaluar VS el modelo más caro?

2. Agregar métricas (NDCG@5, NDCG@10, Recall@5, Recall@10, MRR)

3. gold evaluation set (50 queries)
Este gold eval necesita libros y sus etiquetas, ejemplo:
3 = excellent recommendation
2 = relevant
1 = somewhat relevant
0 = irrelevant
Y después tenemos métricas:
TF-IDF                NDCG@10 = .51
MiniLM                NDCG@10 = .63
MPNet                  NDCG@10 = .68
MPNet + BM25           NDCG@10 = .72
MPNet + CrossEncoder   NDCG@10 = .79
Fine-tuned model       NDCG@10 = .83

4. Probar distintos tokenizers, chunks (Title, title + TOC, title + TOC + description, title + chapter 1 + chapter 2 + chapter 3)

5. No se si sea necesario BM25 para hacer una combinación entre:
                   ┌→ BM25 ────────┐
USER QUERY ────────┤                ├→ combine
                   └→ MPNet ───────┘

6. Bookpath V1 trabajó con un bicoder

QUERY ─→ Transformer ─→ vector Q

BOOK ──→ Transformer ─→ vector B

                  cosine(Q,B)
Podemos usar un CROSS-ENCODER?

7. Hasta aquí no hemos usado neural networks (a mi me gustaría implementar, entrenar, hacer fine-tuning si es posible, qué se necesita?)

8. Como clasificar el nivel de dificultad de los libros (un compañero había hecho como publisher, numero de paginas, 10 reviews, creo que esta es un buen candidato para el features engineering)

9. Log and monitor, with retraining path written down

10. RAG pipelines, agent with guardrails

11. Evals, harness

12. More software features

13. topic modeling, document vector topic (NLP in action mentions it)

14. What type of feedback loop are we going to have? Clicks? Likes? Thumbs up/down?

15. Read the syllabus of this course and see if we can learn/implement something https://maven.com/parlance-labs/evals?promoCode=hamel-dev here is the syllabus /next_steps/ai_evals_or_engineers_syllabus.txt
