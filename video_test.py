from google.cloud import videointelligence_v1 as videointelligence

def main():
    client = videointelligence.VideoIntelligenceServiceClient()

    features = [videointelligence.Feature.LABEL_DETECTION]

    # ローカルファイル読み込み
    with open("/Users/taehyeonglee/Downloads/1753309926185.mp4", "rb") as f:
        input_content = f.read()

    # API呼び出し
    operation = client.annotate_video(
        request={"features": features, "input_content": input_content}
    )

    print("Waiting for operation to complete...")
    result = operation.result(timeout=90)

    # ラベル出力
    for annotation in result.annotation_results:
        for label in annotation.segment_label_annotations:
            print(f"Label: {label.entity.description}")
            for segment in label.segments:
                start = segment.segment.start_time_offset.total_seconds()
                end = segment.segment.end_time_offset.total_seconds()
                confidence = segment.confidence
                print(f"  Segment: {start:.2f}s - {end:.2f}s, confidence={confidence:.2f}")

if __name__ == "__main__":
    main()

