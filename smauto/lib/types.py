class List:
    def __init__(self, parent, items):
        self.parent = parent
        self.items = items

    # String representation of List class that opens up subLists as strings
    def __repr__(self):
        return str(self.print_item(self))

    # List representation to bring out subLists instead of List items
    @staticmethod
    def print_item(item):
        # If item is a list return list of items printed out including sublists
        if type(item) == List:
            return [item.print_item(x) for x in item.items]
        # else if just a primitive, return it as is
        else:
            return item


class Dict:
    def __init__(self, parent, items):
        self.parent = parent
        self.items = items

    # String representation of Dict class that prints subitems as strings
    def __repr__(self):
        final_str = "{"
        for index, item in enumerate(self.items):
            final_str = final_str + f"'{item.name}'" + ":" + str(self.print_item(item.value))
            if index != (len(self.items) - 1):
                final_str = final_str + ','
        final_str = final_str + '}'
        return final_str

    @staticmethod
    def print_item(item):
        # If item is a list return list of items printed out including sublists
        if type(item) == List:
            return [item.print_item(x) for x in item.items]
        # else if just a primitive, return it as is
        else:
            return item

    def to_dict(self):
        return {item.name: item.value for item in self.items}


class Time:
    def __init__(self, parent, hours, minutes, seconds):
        self.parent = parent
        hours = 0 if hours is None else hours
        minutes = 0 if minutes is None else minutes
        seconds = 0 if seconds is None else seconds
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
