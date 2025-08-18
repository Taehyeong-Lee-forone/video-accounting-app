'use client'

import JournalReview from '@/components/JournalReview'

export default function ReviewPage({ params }: { params: { id: string } }) {
  const videoId = parseInt(params.id)

  return (
    <div className="max-w-7xl mx-auto">
      <JournalReview videoId={videoId} />
    </div>
  )
}