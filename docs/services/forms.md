# Google Forms

`FormsService` wraps the Google Forms API v1. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

Note: The Forms API uses `static_discovery=False` when building the service resource.

```python
google = GoogleService(credentials_path="creds.json", services=["forms"])
forms = google.forms
```

## Methods

### get_form

```python
def get_form(self, form_id: str) -> dict[str, Any]
```

Get a form by ID. Returns the full form resource including `formId`, `info`, `items`, and `responderUri`.

```python
form = google.forms.get_form("form_id_here")
print(form["info"]["title"])
for item in form.get("items", []):
    print(item["title"])
```

### list_responses

```python
def list_responses(
    self,
    form_id: str,
    page_size: int = 50,
    page_token: str | None = None,
) -> dict[str, Any]
```

List form responses with pagination. Returns a dict with `responses` (list) and `nextPageToken` (str or None).

```python
result = google.forms.list_responses("form_id_here", page_size=100)
for response in result["responses"]:
    print(response["responseId"])

# Paginate
if result["nextPageToken"]:
    next_page = google.forms.list_responses("form_id_here", page_token=result["nextPageToken"])
```

### get_response

```python
def get_response(self, form_id: str, response_id: str) -> dict[str, Any]
```

Get a specific form response by ID.

```python
response = google.forms.get_response("form_id", "response_id")
for question_id, answer in response.get("answers", {}).items():
    print(question_id, answer["textAnswers"]["answers"])
```

### create_form

```python
def create_form(self, title: str) -> dict[str, Any]
```

Create a new blank form with the given title.

```python
form = google.forms.create_form("Customer Survey")
print(form["formId"])
```

### batch_update

```python
def batch_update(
    self,
    form_id: str,
    requests: list[dict[str, Any]],
) -> dict[str, Any]
```

Apply batch updates to a form. Use this to add questions, update settings, etc.

- `requests`: List of Forms API request objects (see [Google Forms API batchUpdate reference](https://developers.google.com/forms/api/reference/rest/v1/forms/batchUpdate)).

```python
google.forms.batch_update("form_id", [
    {
        "createItem": {
            "item": {
                "title": "What is your name?",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False},
                    }
                },
            },
            "location": {"index": 0},
        }
    }
])
```
