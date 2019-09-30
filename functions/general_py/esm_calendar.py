"""
Module Docstring.,..?
"""
import copy
import logging
import sys


def find_remaining_minutes(seconds):
    """
    Finds the remaining full minutes of a given number of seconds

    Parameters
    ----------
    seconds : int
        The number of seconds to allocate

    Returns
    -------
    int
        The leftover seconds once new minutes have been filled.
    """
    return seconds % 60


# NOTE: This actually kills the docstring, but minutes and seconds are the
# same...
find_remaining_hours = find_remaining_minutes


class Dateformat(object):
    datesep = ["", "-", "-", "-", " ", " ", "", "-", "", "", "/"]
    timesep = ["", ":", ":", ":", " ", ":", ":", "", "", "", ":"]
    dtsep = ["_", "_", "T", " ", " ", " ", "_", "_", "", "_", " "]

    def __init__(self, form=1, printhours=True, printminutes=True, printseconds=True):
        self.form = form
        self.printseconds = printseconds
        self.printminutes = printminutes
        self.printhours = printhours

    def __repr__(self):
        return (
            "Dateformat(form=%s, printhours=%s, printminutes=%s, printseconds=%s)"
            % (self.form, self.printhours, self.printminutes, self.printseconds)
        )


class Calendar(object):
    """
    Class to contain various types of calendars.

    Parameters
    ----------
    calendar_type : int
        The type of calendar to use.

        Supported calendar types:
        0
            no leap years
        1
            proleptic greogrian calendar (default)
        ``n``
            equal months of ``n`` days

    Attributes
    ----------
    timeunits : list of str
        A list of accepted time units.
    monthnames : list of str
        A list of valid month names, using 3 letter English abbreviation.

    Methods
    -------
    isleapyear(year)
        Returns a boolean testing if the given year is a leapyear

    day_in_year(year):
        Returns the total number of days in a given year

    day_in_month(year, month):
        Returns the total number of days in a given month for a given year
        (considering leapyears)
    """

    timeunits = ["years", "months", "days", "hours", "minutes", "seconds"]
    monthnames = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    def __init__(self, calendar_type=1):
        self.calendar_type = calendar_type

    def isleapyear(self, year):
        """
        Checks if a year is a leapyear

        Parameters
        ----------
        year : int
            The year to check

        Returns
        -------
        bool
            True if the given year is a leapyear
        """
        if self.calendar_type == 1:
            if (year % 4) == 0:
                if (year % 100) == 0:
                    if (year % 400) == 0:
                        leapyear = True
                    else:
                        leapyear = False
                else:
                    leapyear = True
            else:
                leapyear = False
        else:
            leapyear = False
        return leapyear

    def day_in_year(self, year):
        """
        Finds total number of days in a year, considering leapyears if the
        calendar type allows for them.

        Parameters
        ----------
        year : int
            The year to check

        Returns
        -------
        int
            The total number of days for this specific calendar type
        """
        if self.calendar_type == 0:
            number_of_days = 365
        elif self.calendar_type == 1:
            number_of_days = 365 + int(self.isleapyear(year))
        else:
            number_of_days = self.calendar_type * 12
        return number_of_days

    def day_in_month(self, year, month):
        """
        Finds the number of days in a given month

        Parameters
        ----------
        year : int
            The year to check
        month : int or str
            The month number or short name.

        Returns
        -------
        int
            The number of days in this month, considering leapyears if needed.

        Raises
        ------
        TypeError
            Raised when you give an incorrect type for month
        """
        if isinstance(month, str):
            month = month.capitalize()  # Clean up possible badly formated month
            month = self.monthnames.index(month) + 1  # Remember, python is 0 indexed
        # Make sure you gave a month from 1 to 12
        if month > 12:
            raise TypeError("You have given an idiotic month, please reconsider")
        elif not isinstance(month, int):
            raise TypeError(
                "You must supply either a str with short month name, or an int!"
            )
        if self.calendar_type == 0 or self.calendar_type == 1:
            if month in [1, 3, 5, 7, 8, 10, 12]:
                return 31
            if month in [4, 6, 9, 11]:
                return 30
            return 28 + int(self.isleapyear(year))
        # I don't really like this, but if the calendar type is not 1 or 0, it
        # is ``n``, with n being the number of days in equal-length months...
        return self.calendar_type

    def __repr__(self):
        return "esm_calendar(calendar_type=%s)" % self.calendar_type

    def __str__(self):
        if self.calendar_type == 0:
            return "esm_calender object with no leap years allowed"
        if self.calendar_type == 1:
            return "esm_calendar object with allowed leap years"
        return (
            "esm_calendar object with equal-length months of %s days"
            % self.calendar_type
        )


class Date(object):
    """
    A class to contain dates, also compatiable with paleo (negative dates)

    Parameters
    ----------
    indate : str
        The date to use.

        See `pyesm.core.time_control.esm_calendar.Dateformat` for available
        formatters.

    calendar : ~`pyesm.core.time_control.esm_calendar.Calendar`, optional
        The type of calendar to use. Defaults to a greogrian proleptic calendar
        if nothing is specified.

    Attributes
    ----------
    year : int
        The year
    month : int
        The month
    day : int
        The day
    hour : int
        The hour
    minute : int
        The minute
    second : int
        The second
    _calendar : ~`pyesm.core.time_control.esm_calendar.Calendar`
        The type of calendar to use

    Methods
    -------
    """

    def __init__(self, indate, calendar=Calendar()):
        printhours = True
        printminutes = True
        printseconds = True
        ndate = ["1900", "01", "01", "00", "00", "00"]
        ds = ""
        ts = ""
        if "T" in indate:
            indate2 = indate.replace("T", "_")
            ts = ":"
        else:
            indate2 = indate
        if "_" in indate2:
            date, time = indate2.split("_")
        else:
            date = indate2
            time = ""
            ts = ":"
        for index in [3, 4, 5]:
            if len(time) == 2:
                ndate[index] = time
                time = time[2:]
            elif len(time) > 2:
                ndate[index] = time[:2]
                if len(time) > 2:
                    time = time[2:]
                    if time[0] == ":":
                        time = time[1:]
                        ts = ":"
            else:
                ndate[index] = "00"
                if index == 3:
                    printhours = False
                elif index == 4:
                    printminutes = False
                elif index == 5:
                    printseconds = False
        for index in [2, 1]:
            ndate[index] = date[-2:]
            date = date[:-2]
            if len(date) > 0 and date[-1] == "-":
                date = date[:-1]
                ds = "-"
        ndate[0] = date
        if ds == "-" and ts == ":":
            if "T" not in indate:
                form = 1
            else:
                form = 2
        elif ds == "-" and ts == "":
            form = 7
        elif ds == "" and ts == ":":
            form = 6
        elif ds == "" and ts == "":
            form = 9
        self.year, self.month, self.day, self.hour, self.minute, self.second = map(
            int, ndate
        )
        self.syear, self.smonth, self.sday, self.shour, self.sminute, self.ssecond = map(
            str, ndate
        )

        self._calendar = calendar
        self.doy = self.day_of_year()
        self.sdoy = str(self.day_of_year())

        self._date_format = Dateformat(form, printhours, printminutes, printseconds)

    @property
    def sdoy(self):
        return self.__sdoy

    @sdoy.setter
    def sdoy(self, sdoy):
        self.__sdoy = str(self.doy)

    @property
    def syear(self):
        return self.__syear

    @syear.setter
    def syear(self, syear):
        self.__syear = str(self.year)

    @property
    def smonth(self):
        return self.__smonth

    @smonth.setter
    def smonth(self, smonth):
        self.__smonth = str(self.month).zfill(2)

    @property
    def sday(self):
        return self.__sday

    @sday.setter
    def sday(self, sday):
        self.__sday = str(self.day).zfill(2)

    @property
    def shour(self):
        return self.__shour

    @shour.setter
    def shour(self, shour):
        self.__shour = str(self.hour).zfill(2)

    @property
    def sminute(self):
        return self.__sminute

    @sminute.setter
    def sminute(self, sminute):
        self.__sminute = str(self.minute).zfill(2)

    @property
    def ssecond(self):
        return self.__ssecond

    @ssecond.setter
    def ssecond(self, ssecond):
        self.__ssecond = str(self.second).zfill(2)

    def output(self, form="SELF"):
        return self.format(form)

    @classmethod
    def from_list(cls, _list):
        """
        Creates a new Date from a list

        Parameters
        ----------
        _list : list of ints
            A list of [year, month, day, hour, minute, second]

        Returns
        -------
        date : ~`pyesm.core.time_control.esm_calendar.Date`
            A new date of year month day, hour minute, second
        """
        negative_year = (
            negative_month
        ) = negative_day = negative_hour = negative_minute = negative_second = False

        if _list[0] < 0:
            negative_year = True
            _list[0] *= -1
        if _list[1] < 0:
            negative_month = True
            _list[1] *= -1
        if _list[2] < 0:
            negative_day = True
            _list[2] *= -1
        if _list[3] < 0:
            negative_hour = True
            _list[3] *= -1
        if _list[4] < 0:
            negative_minute = True
            _list[4] *= -1
        if _list[5] < 0:
            negative_second = True
            _list[5] *= -1

        year = str(_list[0]).zfill(4)
        month = str(_list[1]).zfill(2)
        day = str(_list[2]).zfill(2)
        hour = str(_list[3]).zfill(2)
        minute = str(_list[4]).zfill(2)
        second = str(_list[5]).zfill(2)

        if negative_year:
            year = "-" + year
        if negative_month:
            month = "-" + month
        if negative_day:
            day = "-" + day
        if negative_hour:
            hour = "-" + hour
        if negative_minute:
            minute = "-" + minute
        if negative_second:
            second = "-" + second

        indate = (
            year + "-" + month + "-" + day + "_" + hour + ":" + minute + ":" + second
        )
        return cls(indate)

    fromlist = from_list

    def __repr__(self):
        return "Date(%s-%s-%sT%s:%s:%s)" % (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )

    def __getitem__(self, item):
        return (self.year, self.month, self.day, self.hour, self.minute, self.second)[
            item
        ]

    def __setitem__(self, item, value):
        value = int(value)
        if item == 0:
            self.year = value
        elif item == 1:
            self.month = value
        elif item == 2:
            self.day = value
        elif item == 3:
            self.hour = value
        elif item == 4:
            self.minute = value
        elif item == 5:
            self.second = value
        else:
            raise IndexError("You can only assign up to 5!")

    def __lt__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup < other_tup

    def __le__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup <= other_tup

    def __eq__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup == other_tup

    def __ne__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup != other_tup

    def __ge__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup >= other_tup

    def __gt__(self, other):
        self_tup = (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )
        other_tup = (
            other.year,
            other.month,
            other.day,
            other.hour,
            other.minute,
            other.second,
        )
        return self_tup > other_tup

    def __sub__(self, other):
        # FIXME / BUG -- d1 and d2 are actually modified in this function. That's bad.
        d2 = copy.deepcopy(
            [self.year, self.month, self.day, self.hour, self.minute, self.second]
        )
        d1 = copy.deepcopy(
            [other.year, other.month, other.day, other.hour, other.minute, other.second]
        )

        diff = [0, 0, 0, 0, 0, 0]

        #        for description, i in zip(["second", "minute", "day", "month", "year"], [5, 4, 3, 2, 1, 0]):
        #            print(description, "other date", d2[i], "this date", d1[i])
        #            diff[i] += d2[i] - d1[i]
        #            print(diff)
        #            if diff[i] < 0:
        #                diff[i-1] -= 1

        while d1[1] > 1:
            diff[1] -= 1
            d1[1] -= 1
            diff[2] -= self._calendar.day_in_month(d1[0], d1[1])

        while d2[1] > 1:
            diff[1] += 1
            d2[1] -= 1
            diff[2] += self._calendar.day_in_month(d2[0], d2[1])

        if diff[1] < 0:
            diff[0] = diff[0] - 1

        while d1[0] > d2[0]:
            diff[0] += 1
            diff[1] += 12
            diff[2] += self._calendar.day_in_year(d1[0])
            d2[0] += 1

        diff[3] += diff[2] * 24
        if diff[3] < 0:
            diff[3] += 24
        diff[4] += diff[3] * 60
        if diff[4] < 0:
            diff[4] += 60
        diff[5] += diff[4] * 60
        if diff[5] < 0:
            diff[5] += 60

        return diff

    def time_between(self, date, outformat="seconds"):
        """
        Computes the time between two dates

        Parameters
        ----------
        date : ~`pyesm.core.time_control.date`
            The date to compare against.

        Returns
        -------
        ??
        """
        if date > self:
            diff = date - self
        else:
            diff = self - date

        for index in range(0, 6):
            if outformat == self._calendar.timeunits[index]:
                # FIXME: Wouldn't this stop after the very first index that matches?
                # I think that is the point, but I'm not sure.
                return diff[index]
        return None  # ...? Or raise an error?

    def day_of_year(self):
        """
        Gets the day of the year, counting from Jan. 1

        Returns
        -------
        int
            The day of the current year.
        """
        if self[1] == self[2] == 1:
            return 1
        else:
            date2 = Date(str(self[0]) + "-01-01T00:00:00", self._calendar)
            return self.time_between(date2, "days") + 1

    def __str__(self):
        return (
            "-".join([str(self.year), str(self.month).zfill(2), str(self.day).zfill(2)])
            + "T"
            + ":".join(
                [
                    str(self.hour).zfill(2),
                    str(self.minute).zfill(2),
                    str(self.second).zfill(2),
                ]
            )
        )

    def format(
        self, form="SELF", givenph=None, givenpm=None, givenps=None
    ):  # basically format_date
        """
        Needs a docstring!
        The following forms are accepted:
        + SELF: uses the format which was given when constructing the date
        + 0: A Date formated as YYYY

        In [5]: test.format(form=1)
        Out[5]: '1850-01-01_00:00:00'

        In [6]: test.format(form=2)
        Out[6]: '1850-01-01T00:00:00'

        In [7]: test.format(form=3)
        Out[7]: '1850-01-01 00:00:00'

        In [8]: test.format(form=4)
        Out[8]: '1850 01 01 00 00 00'

        In [9]: test.format(form=5)
        Out[9]: '01 Jan 1850 00:00:00'

        In [10]: test.format(form=6)
        Out[10]: '18500101_00:00:00'

        In [11]: test.format(form=7)
        Out[11]: '1850-01-01_000000'

        In [12]: test.format(form=8)
        Out[12]: '18500101000000'

        In [13]: test.format(form=9)
        Out[13]: '18500101_000000'

        In [14]: test.format(form=10)
        Out[14]: '01/01/1850 00:00:00'
        """
        if form == "SELF":
            form = self._date_format.form

        ph = self._date_format.printhours
        pm = self._date_format.printminutes
        ps = self._date_format.printseconds

        if not givenph == None:
            ph = givenph
        if not givenpm == None:
            pm = givenpm
        if not givenps == None:
            ps = givenps
        ndate = list(
            map(
                str,
                (
                    self.year,
                    self.smonth,
                    self.sday,
                    self.shour,
                    self.sminute,
                    self.ssecond,
                ),
            )
        )
        if form == 0:
            if len(ndate[0]) < 4:
                for _ in range(1, 4 - len(ndate[0])):
                    ndate[0] = "0" + ndate[0]
        elif form == 5:
            temp = ndate[0]
            ndate[0] = ndate[2]
            ndate[2] = temp
            ndate[1] = self._calendar.monthnames[int(ndate[1]) - 1]
        elif form == 8:
            if len(ndate[0]) < 4:
                print("Format 8 clear with 4 digit year only")
                sys.exit(2)
        elif form == 10:
            temp = ndate[0]
            ndate[0] = ndate[1]
            ndate[1] = ndate[2]
            ndate[2] = temp

        for index in range(0, 6):
            if len(ndate[index]) < 2:
                ndate[index] = "0" + ndate[index]

        ndate[1] = self._date_format.datesep[form] + ndate[1]
        ndate[2] = self._date_format.datesep[form] + ndate[2]
        ndate[3] = self._date_format.dtsep[form] + ndate[3]
        ndate[4] = self._date_format.timesep[form] + ndate[4]
        ndate[5] = self._date_format.timesep[form] + ndate[5]

        if not ps:
            ndate[5] = ""
        if not pm and ndate[5] == "":
            ndate[4] = ""
        if not ph and ndate[4] == "":
            ndate[3] = ""

        return ndate[0] + ndate[1] + ndate[2] + ndate[3] + ndate[4] + ndate[5]

    def makesense(self):
        """
        Puts overflowed time back into the correct unit.

        When manipulating the date, it might be that you have "70 seconds", or
        something similar. Here, we put the overflowed time into the
        appropriate unit.
        """
        ndate = copy.deepcopy(self)
        ndate[4] = ndate[4] + ndate[5] / 60
        ndate[5] = ndate[5] % 60

        ndate[3] = ndate[3] + ndate[4] / 60
        ndate[4] = ndate[4] % 60

        ndate[2] = ndate[2] + ndate[3] / 24
        ndate[3] = ndate[3] % 24

        while ndate[2] > self._calendar.day_in_month(ndate[0], ndate[1]):
            ndate[2] = ndate[2] - self._calendar.day_in_month(ndate[0], ndate[1])
            ndate[1] = ndate[1] + 1

        ndate[0] = ndate[0] + (ndate[1] - 1) / 12
        ndate[1] = (ndate[1] - 1) % 12 + 1

        while ndate[2] <= 0:
            ndate[1] = ndate[1] - 1
            if ndate[1] == 0:
                ndate[1] = 12
                ndate[0] = ndate[0] - 1
            ndate[2] = ndate[2] + self._calendar.day_in_month(ndate[0], ndate[1])

        if ndate[1] == 0:
            ndate[1] = 12
            ndate[0] = ndate[0] - 1

        print ("888888888888888888888888888888888888888888888 ", str(ndate))

        self.year, self.month, self.day, self.hour, self.minute, self.second = map(
            int, ndate
        )
        self.syear, self.smonth, self.sday, self.shour, self.sminute, self.ssecond = map(
            str, ndate
        )
        print (str(self.day), self.sday)

    def add(self, to_add):
        """
        Adds another date to this one.

        Parameters
        ----------
        to_add : ~`pyesm.core.time_control.Date`
            The other date to add to this one.

        Returns
        -------
        new_date : ~`pyesm.core.time_control.Date`
            A new date object with the added dates
        """
        new_year = self.year + to_add[0]
        new_month = self.month + to_add[1]
        new_day = self.day + to_add[2]
        new_hour = self.hour + to_add[3]
        new_minute = self.minute + to_add[4]
        new_second = self.second + to_add[5]
        new_date = self.from_list(
            [new_year, new_month, new_day, new_hour, new_minute, new_second]
        )
        new_date.makesense()
        return new_date

    __add__ = add

    def sub(self, to_sub):
        """
        Adds another date to from one.

        Parameters
        ----------
        to_sub : ~`pyesm.core.time_control.Date`
            The other date to sub from this one.

        Returns
        -------
        new_date : ~`pyesm.core.time_control.Date`
            A new date object with the subtracted dates
        """
        logging.debug("Subtracting %s %s", self, to_sub)
        # Probably, this also does something with modifing the actual values.
        # Better to just make a copy of everything:
        original = copy.deepcopy(self)
        logging.debug("SUB: %s, %s", original.year, to_sub[0])
        new_year = original.year - to_sub[0]
        logging.debug(new_year)

        logging.debug("SUB: %s, %s", original.month, to_sub[1])
        new_month = original.month - to_sub[1]
        logging.debug(new_month)

        logging.debug("SUB: %s, %s", original.day, to_sub[2])
        new_day = original.day - to_sub[2]
        logging.debug(new_day)

        logging.debug("SUB: %s, %s", original.hour, to_sub[3])
        new_hour = original.hour - to_sub[3]
        logging.debug(new_hour)

        logging.debug("SUB: %s, %s", original.minute, to_sub[4])
        new_minute = original.minute - to_sub[4]
        logging.debug(new_minute)

        logging.debug("SUB: %s, %s", original.second, to_sub[5])
        new_second = original.second - to_sub[5]
        logging.debug(new_second)

        logging.debug([new_year, new_month, new_day, new_hour, new_minute, new_second])
        new_date = original.from_list(
            [new_year, new_month, new_day, new_hour, new_minute, new_second]
        )
        logging.debug("new_date after sub: %s", new_date)
        logging.debug("makesense start...")
        new_date.makesense()
        logging.debug("After makesense: %s", new_date)
        return new_date
