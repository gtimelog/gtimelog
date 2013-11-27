To use Thunderbird with GTimeLog, put this bit into ~/.gtimelog/gtimelogrc:

  mailer = S='%s'; thunderbird -compose "to='$(cat $S|head -1|sed -e "s/^To: //")',subject='$(cat $S|head -2|tail -1|sed -e "s/^Subject: //")',body='$(cat $S|tail -n +4)'"

It needs to be a single line.

Source: http://d9t.de/blog/gtimelog-mit-thunderbird (Daniel Kraft)
