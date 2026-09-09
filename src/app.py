import streamlit as st

from rag_graph_v4 import process_question


st.set_page_config(
    page_title="ByteKnights Archive Assistant",
    page_icon="📚",
    layout="wide"
)


st.title(
    "📚 ByteKnights – Ashen Era Archive Assistant"
)

st.write(
    "Ask questions across the Ashen Era Archive using "
    "graph-assisted multi-hop RAG and visual retrieval."
)


question = st.text_input(
    "Ask a question:",
    placeholder=(
        "Example: Which war did Ravena Stormwell's "
        "own faction ultimately win?"
    )
)


ask_button = st.button(
    "Ask ByteKnights"
)


if ask_button:

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        with st.spinner(
            "Searching the Ashen Era Archive..."
        ):

            result = process_question(
                question
            )

        if result:

            st.divider()

            if result["mode"] == "visual":
                st.info(
                    "🖼️ Visual evidence pipeline used"
                )

            elif result["mode"] == "text":
                st.info(
                    "🔗 Graph-assisted multi-hop RAG used"
                )

            st.subheader(
                "Answer"
            )

            st.markdown(
                result["answer"]
            )

            # ---------------------------------------------
            # VISUAL RESULT
            # ---------------------------------------------

            if (
                result["mode"] == "visual"
                and result["image"]
            ):

                st.subheader(
                    "Image Evidence"
                )

                st.image(
                    result["image"],
                    use_container_width=False
                )

            # ---------------------------------------------
            # TEXT SOURCES
            # ---------------------------------------------

            if result["sources"]:

                st.subheader(
                    "Evidence Sources"
                )

                for number, source in enumerate(
                    result["sources"],
                    start=1
                ):

                    title = (
                        f"Evidence {number}: "
                        f"{source['source']}"
                    )

                    if source["page"] is not None:

                        title += (
                            f" — Page {source['page']}"
                        )

                    with st.expander(
                        title
                    ):

                        if source["score"] is not None:

                            st.write(
                                f"Retrieval score: "
                                f"{source['score']:.4f}"
                            )

                        st.write(
                            source["text"]
                        )