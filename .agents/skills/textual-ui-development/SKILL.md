# Textual UI development

Use this skill when changing the Textual interface in `experiment_server`.

## Range-dependent input validation

For inputs whose validity depends on a peer input, use a `Validator` subclass rather than a closure passed to `Function`. The validator should:

- receive the peer widget ID and whether it validates the minimum or maximum field;
- return a `ValidationResult` from `success()` or `failure()`;
- reject non-integer values without raising;
- allow an empty current value while the user is clearing and replacing it;
- return success when the peer is empty or temporarily invalid, so the user can edit the other field;
- catch DOM lookup and peer-conversion errors because validation can run before the peer is mounted or while the peer contains an intermediate value.

Example shape:

```python
class RangeBoundValidator(Validator):
    def __init__(self, peer_input_id: str, is_min_field: bool) -> None:
        super().__init__()
        self.peer_input_id = peer_input_id
        self.is_min_field = is_min_field

    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.success()
        try:
            current_num = int(value)
        except ValueError:
            return self.failure("Must be a valid integer.")

        try:
            peer = self.screen.query_one(f"#{self.peer_input_id}", Input)
            if not peer.value:
                return self.success()
            peer_num = int(peer.value)
        except (LookupError, ValueError, AttributeError):
            return self.success()

        if self.is_min_field and current_num >= peer_num:
            return self.failure("From must be less than To.")
        if not self.is_min_field and current_num <= peer_num:
            return self.failure("To must be greater than From.")
        return self.success()
```

The event handler must still parse both visible fields before enabling an action such as Update. Field-level validation only describes the field that changed, and the peer may contain an intermediate string such as `-`. Keep both conversions inside one `try` block, treat an empty field as its placeholder/default where that is the UI contract, and leave the action disabled on `ValueError`. Do not infer that the pair is valid from only `event.validation_result`.

Keep the stored range values updated when a conversion succeeds, including when the pair is temporarily invalid. This lets editing the other endpoint recover without stale state. Set the ready flag and enable the button only after both fields parse and the complete pair satisfies the strict ordering rule.

## Review and validation

Keep changes narrowly scoped. Check staged diffs with `git diff --cached --check`, compile changed Python files with `python -m compileall`, and run the repository's configured tests and type checks when their dependencies are available. Separate confirmed defects from environment failures such as missing test tools. For Textual CSS, scope compound selectors explicitly, for example:

```css
#example_ordering_edit Input,
#example_ordering_edit Button {
    width: 20;
}
```

A selector such as `#example_ordering_edit Input,Button` scopes only the first selector and applies the button rule globally.
