import json

class BatchTester:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "link": ("*", ),
                "input": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
                "comments": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
            },
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "validate"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def validate(self, link, input, comments):
        try:
            json_input = json.loads(input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
        if not isinstance(json_input, dict):
            raise ValueError("Input must be a JSON object")
    
        for key, value in json_input.items():
            if not isinstance(key, str):
                raise ValueError(f"Keys must be strings, got {type(key).__name__}")
    
            if isinstance(value, list):
                if not all(isinstance(item, str) for item in value):
                    raise ValueError(f"All items in the list must be strings at key '{key}'")
            elif isinstance(value, dict):
                required_keys = {'min', 'max', 'step'}
                if set(value.keys()) != required_keys:
                    raise ValueError(f"Object at key '{key}' must have keys {required_keys}")
                for k in required_keys:
                    if not isinstance(value[k], (int, float)):
                        raise ValueError(f"Value of '{k}' at key '{key}' must be a number")
            else:
                raise ValueError(
                    f"Value at key '{key}' must be either a list of strings or an object with 'min', 'max', 'step'"
                )
        print("Validation successful")
        return ()

NODE_CLASS_MAPPINGS = {
    "Genera.BatchTester": BatchTester,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.BatchTester": "Batch Tester",
}