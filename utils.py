# wildcard trick is taken from pythongossss's
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_typ = AnyType("*")

class MakeListFromText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"text": ("STRING", ), },
        }

    RETURN_TYPES = (any_typ,)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "doit"

    CATEGORY = "ImpactPack/Util"

    def doit(self, text):
        values = [x.strip() for x in text.split(",")]

        return (values, )


NODE_CLASS_MAPPINGS = {
    "Genera.Utils": MakeListFromText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.Utils": "Make List From Text",
}