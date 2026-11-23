# Recording a firing

When a sensor does not do what you expect during a firing, a recording shows
whether myKiln reported something unexpected or the integration misread it.

## Before the firing

1. *Settings → Devices & services → ROHDE myKiln → Configure.*
2. Set *Update interval* to 30 and turn on *Record raw data*.
3. The integration reloads and logs where it records to, for example
   `/config/rohde_mykiln_capture/20261124-081500.jsonl`. Every restart or options
   change starts a new file.

## During the firing

Write down the time and what the kiln display or the myKiln app shows at these moments
(phone screenshots of the app work well, they carry the time):

- start of the program (and a delayed start, if used)
- end of each ramp and each hold
- end of the program
- cooling, and when the kiln is cool again
- the kiln going offline or coming back

When an entity in Home Assistant looks wrong, note the time and the entity.

## After the firing

1. Turn *Record raw data* off again. A day at 30 s polling is a few MB.
2. Get the file from the `rohde_mykiln_capture` folder (Samba share, File editor,
   Studio Code Server or SSH add-on).
3. Look at the timeline:

   ```
   python tools/replay_capture.py 20261124-081500.jsonl
   python tools/replay_capture.py 20261124-081500.jsonl --raw          # also raw field changes
   python tools/replay_capture.py 20261124-081500.jsonl --csv firing.csv
   ```

## What is in the file

One JSON object per line, each with `time` and `kind`:

| kind | content |
| --- | --- |
| `start` | Home Assistant version and update interval |
| `status` | the raw `/kilns_get_status/` response |
| `parsed` | what the integration made of it, per kiln |
| `kiln_list` | the kiln list page (account email replaced by `<email>`) and what was read from it |
| `login`, `session_expired` | re-login attempts and why |
| `error` | a poll that failed |

No password or session cookie is written. The file does contain kiln and controller
serial numbers and IDs: check it before you share it publicly. To keep a firing as a
test case, put a copy in `tests/captures/`; `pytest` then runs it through the parser.
