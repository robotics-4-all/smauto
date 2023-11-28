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
            final_str = (
                final_str + f"'{item.name}'" + ":" + str(self.print_item(item.value))
            )
            if index != (len(self.items) - 1):
                final_str = final_str + ","
        final_str = final_str + "}"
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
    def __init__(self, parent, hour, minute, second):
        self.parent = parent
        hour = 0 if hour is None else hour
        minute = 0 if minute is None else minute
        second = 0 if second is None else second
        self.hour = hour
        self.minute = minute
        self.second = second

    def to_int(self):
        val = self.second + int(self.minute << 8) + int(self.hour << 16)
        return val


class Date:
    def __init__(self, parent, month, day, year):
        self.parent = parent
        self.month = month
        self.day = day
        self.year = year
