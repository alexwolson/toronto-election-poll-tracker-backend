# Use reader-visible race history for aggregate hints

Status: accepted

Aggregate Historical hints use every confirmed elected-office Candidacy strictly before the
subject Contest, including council races; a hint may instead name one Office type explicitly.
All-races-except-council and conditional council-history unions are ineligible even when they show
a statistical association, because their qualifying count conflicts with the complete history a
reader sees. Incumbency is handled by Candidate-regime adjustment or explicit stratification. This
costs some previously supported hints, but prevents the frontend from presenting an unexplained
internal subset as a candidate's record.
