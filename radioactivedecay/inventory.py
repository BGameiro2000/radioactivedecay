"""
The inventory module defines the ``Inventory`` class. Each ``Inventory`` instance contains one or
more radionuclides, each with an associated number. The decay of the radionuclide(s) in an
``Inventory`` can be calculated by using the ``decay()`` method (normal double-precision
floating-point operations). Use the ``decay_high_precision()`` method to perform a SymPy high
numerical precision calculation. A ``DecayData`` dataset associated with each ``Inventory``
instance is the radioactive decay data source (default is rd.DEFAULTDATA).

The code examples shown in the docstrings assume the ``radioactivedecay`` package has been imported
as:

.. highlight:: python
.. code-block:: python

    >>> import radioactivedecay as rd

"""

from functools import singledispatch, update_wrapper
from typing import Callable, Dict, List, Tuple, Union
import matplotlib
from sympy import exp, nsimplify
from scipy.constants import Avogadro
from radioactivedecay.decaydata import DecayData, DEFAULTDATA, np
from radioactivedecay.plots import _decay_graph
from radioactivedecay.radionuclide import Radionuclide
from radioactivedecay.utils import (
    parse_radionuclide,
    time_unit_conv,
    time_unit_conv_sympy,
)


# pylint: disable=too-many-arguments, too-many-locals


def _add_dictionaries(
    dict_a: Dict[str, float], dict_b: Dict[str, float]
) -> Dict[str, float]:
    """
    Adds together two dictionaries of radionuclides and associated numbers.

    Parameters
    ----------
    dict_a : dict
        First dictionary containing radionuclide strings as keys and numbers as values.
    dict_b : dict
        Second dictionary containing radionuclide strings as keys and numbers as values.

    Returns
    -------
    dict
        Combined dictionary containing the radionuclides in both dict_a and dict_b, where
        numbers have been added together when a radionuclide is present in both input
        dictionaries.

    Examples
    --------
    >>> dict_a = {'Pm-141': 1.0, 'Rb-78': 2.0}
    >>> dict_b = {'Pm-141': 3.0, 'Rb-90': 4.0}
    >>> rd.inventory._add_dictionaries(dict_a, dict_b)
    {'Pm-141': 4.0, 'Rb-78': 2.0, 'Rb-90': 4.0}

    """

    new_dict = dict_a.copy()
    for radionuclide, number in dict_b.items():
        if radionuclide in new_dict:
            new_dict[radionuclide] = new_dict[radionuclide] + number
        else:
            new_dict[radionuclide] = number

    return new_dict


def _activity_to_number(
    radionuclide: str,
    activity : float,
    data: DecayData = DEFAULTDATA
) -> float:
    """
    Converts activity to number of atoms.

    Parameters
    ----------
    radionuclide : str
        The name of the material to be converted.
    activity : float
        The activity of the material to be converted.
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Returns
    -------
    float
        Number of atoms of material.

    Example
    --------
    >>> rd.inventory._activity_to_number("C-14", 250)
    64876004584874.73

    """

    try:
        index = data.radionuclide_dict[radionuclide]
    except:
        raise ValueError(
            radionuclide
            + " is not a valid member of "
            + data.dataset
            )
        
    return (activity / data.scipy_data.decay_consts[index])


def _mass_to_number(
    radionuclide: str,
    mass : float,
    data: DecayData = DEFAULTDATA
) -> float:
    """
    Converts a mass to number of atoms.

    Parameters
    ----------
    radionuclide : str
        The name of the material to be converted.
    mass : float
        The mass of the material to be converted in grams.
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Returns
    -------
    float
        Number of atoms of material.

    Example
    --------
    >>> rd.inventory._mass_to_number("Fe-56", 25)
    2.6915829535623837e+23

    """

    try:
        index = data.radionuclide_dict[radionuclide]
    except:
        raise ValueError(
            radionuclide
            + " is not a valid member of "
            + data.dataset
            )

    return (mass / data.masses[index] * Avogadro)


def _moles_to_number(moles : float) -> float:
    """
    Converts number of moles to number of atoms.

    Parameters
    ----------
    moles : float
        The moles of material to be converted.

    Returns
    -------
    float
        Number of atoms of material.

    Example
    --------
    >>> rd.inventory._moles_to_number(.2)
    1.204428152e+23

    """

    return moles * Avogadro


def _number_to_activity(
    radionuclide: str,
    number : float,
    data: DecayData = DEFAULTDATA
) -> float:
    """
    Converts number of atoms to activity.

    Parameters
    ----------
    radionuclide : str
        The name of the material to be converted.
    number : float
        The number of atoms of material to be converted.
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Returns
    -------
    float
        Activity of the material.

    Examples
    --------
    >>> rd.inventory._number_to_activity("U-238", 3 * 10**23)
    1474819.4578951003

    """

    try:
        index = data.radionuclide_dict[radionuclide]
    except:
        raise ValueError(
            radionuclide
            + " is not a valid member of "
            + data.dataset
            )
    
    return (number * data.scipy_data.decay_consts[index])


def _number_to_mass(
    radionuclide: str,
    number : float,
    data: DecayData = DEFAULTDATA
) -> float:
    """
    Converts number of atoms to mass in grams.

    Parameters
    ----------
    radionuclide : str
        The name of the material to be converted.
    number : float
        The number of atoms of the material to be converted.
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Returns
    -------
    float
        Mass of material in grams.

    Examples
    --------
    >>> rd.inventory._number_to_mass("Fe-56", 3 * 10**23)
    27.86464370371177

    """

    try:
        index = data.radionuclide_dict[radionuclide]
    except:
        raise ValueError(
            radionuclide
            + " is not a valid member of "
            + data.dataset
            )
    
    return (number / Avogadro * data.masses[index])


def _number_to_moles(number: float) -> float:
    """
    Converts number of atoms to moles of material.

    Parameters
    ----------
    number : float
        The number of atoms of the material to be converted.

    Returns
    -------
    float
        Moles of material.

    Examples
    --------
    >>> rd.inventory._number_to_moles(3 * 10**23)
    0.49816172015215404

    """
    
    return number / Avogadro


def _sort_dictionary_alphabetically(
    input_inv_dict: Dict[str, float]
) -> Dict[str, float]:
    """
    Sorts a dictionary alphabetically by its keys.

    Parameters
    ----------
    input_inv_dict : dict
        Dictionary containing radionuclide strings or Radionuclide objects as keys and numbers
        as values.

    Returns
    -------
    dict
        Inventory dictionary which has been sorted by the radionuclides alphabetically.

    Examples
    --------
    >>> rd.inventory._sort_dictionary_alphabetically({'U-235': 1.2, 'Tc-99m': 2.3, 'Tc-99': 5.8})
    {'Tc-99': 5.8, 'Tc-99m': 2.3, 'U-235': 1.2}

    """

    return dict(sorted(input_inv_dict.items(), key=lambda x: x[0]))


def _input_to_number(
    input_inv_dict: Dict[str, float],
    input_type : str,
    data: DecayData = DEFAULTDATA
) -> Dict[str, float]:
    """
    Converts mass, moles, or activity input inventory dictionary into number.

    Parameters
    ----------
    input_inv_dict : dict
        Dictionary containing radionuclide strings or Radionuclide objects as keys and mass,
        numbers in moles, or activity as values.
    input_type : str
        Format of the input.
    data : DecayData
        Decay dataset (default is the ICRP-107 dataset).
    

    Returns
    -------
    dict
        Inventory dictionary which has values converted to number of the nuclide.

    Raises
    ------
    ValueError
        If the input dictionary values or input type are invalid.

    Examples
    --------
    >>> rd.inventory._input_to_number({'Ni-56': .3, 'Co-56': .7}, "activity")
    {'Ni-56': 227172.53191853972, 'Co-56': 6738641.562715049}
    >>> rd.inventory._input_to_number({'U-238': 21.1, 'Co-57': 7.2}, "mass")
    {'U-238': 5.337817684684321e+22, 'Co-57': 7.61542657764305e+22}

    """
    
    number_abundance_dict, number_dict = {}, {}
    
    if input_type == "masses":
        for nuc, mass in input_inv_dict.items():
            number = _mass_to_number(nuc, mass, data)
            number_dict[nuc] = number
        converted_dict = number_dict.copy()
    elif input_type == "activities":
        for nuc, act in input_inv_dict.items():
            number = _activity_to_number(nuc, act, data)
            number_dict[nuc] = number
        converted_dict = number_dict.copy()
    elif input_type == "moles":
        for nuc, moles in input_inv_dict.items():
            number = _moles_to_number(nuc, moles, data)
            number_dict[nuc] = number
        converted_dict = number_dict.copy()
    else:
        raise ValueError(
            input_type
            + " is not a valid value input type"
        )

    return converted_dict


def _check_dictionary(
    input_inv_dict: Dict[Union[str, Radionuclide], float],
    radionuclides: List[str],
    input_type: str = "activities",
    data: DecayData = DEFAULTDATA
) -> Dict[str, float]:
    """
    Checks validity of a dictionary of radionuclides and associated numbers. Radionuclides must
    be in the decay dataset. Radionuclide strings are parsed to to Ab-XX format.

    Parameters
    ----------
    input_inv_dict : dict
        Dictionary containing radionuclide strings or Radionuclide objects as keys and numberss
        as values.
    radionuclides : List[str]
        List of all the radionuclides in the decay dataset.
    input_type : str, optional
        Type of input (numbers, masses (abundance), or activities), default is activities.
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Returns
    -------
    dict
        Dictionary where the contents have been validated and the keys (radionuclide strings) have
        been parsed into symbol - mass number format.

    Raises
    ------
    ValueError
        If an activity key is invalid.

    Examples
    --------
    >>> rd.inventory._check_dictionary({'3H': 1.0}, rd.DEFAULTDATA.radionuclides, "numbers", rd.DEFAULTDATA.dataset)
    {'H-3': 1.0}
    >>> H3 = rd.Radionuclide('H-3')
    >>> rd.inventory._check_dictionary({H3: 1.0}, rd.DEFAULTDATA.radionuclides, "numbers", rd.DEFAULTDATA.dataset)
    {'H-3': 1.0}

    """

    parsed_inv_dict: Dict[str, float] = {
        (
            parse_radionuclide(nuc.radionuclide, radionuclides, data.dataset)
            if isinstance(nuc, Radionuclide)
            else parse_radionuclide(nuc, radionuclides, data.dataset)
        ): inp
        for nuc, inp in input_inv_dict.items()
    }
    for nuc, inp in parsed_inv_dict.items():
        if not isinstance(inp, (float, int)):
            raise ValueError(
                str(inp) + " is not a valid input for " + str(nuc) + "."
            )

    if input_type != "numbers":
        inv_dict = _input_to_number(parsed_inv_dict, input_type, data).copy()
    else:
        inv_dict = parsed_inv_dict.copy()

    return inv_dict


def _sort_list_according_to_dataset(
    input_list: List[str], key_dict: Dict[str, int]
) -> List[str]:
    """
    Sorts a list of radionuclides based on their order of appearence in the decay dataset.

    Parameters
    ----------
    input_list : list
        List of radionuclide strings to be sorted.
    key_dict : dict
        Dictionary from the decay dataset with radionuclide strings as keys and their position
        (integers) in the decay dataset.

    Returns
    -------
    list
        Sorted radionuclide list.

    Examples
    --------
    >>> rd.inventory._sort_list_according_to_dataset(['Tc-99', 'Tc-99m'], rd.DEFAULTDATA.radionuclide_dict)
    ['Tc-99m', 'Tc-99']

    """

    return sorted(input_list, key=lambda radionuclide: key_dict[radionuclide])


def _method_dispatch(func):
    """Adds singledispatch support for class methods."""

    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        return dispatcher.dispatch(args[1].__class__)(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


class Inventory:
    """
    ``Inventory`` instances store a dictionary of radionuclides and associated numbers, and a
    ``DecayData`` instance of radioactive decay data.

    Parameters
    ----------
    contents : dict
        Dictionary containing radionuclide strings or Radionuclide objects as keys and numbers
        as values.
    input_type : str, optional
        Type of input (masses, numbers, activities; activities is default)
    check : bool, optional
        Check for the validity of contents (default is True).
    data : DecayData, optional
        Decay dataset (default is the ICRP-107 dataset).

    Attributes
    ----------
    numbers : dict
        Dictionary containing radionuclide strings as keys and numbers as values. Radionuclides
        in contents are sorted alphabetically.
    data : DecayData
        Decay dataset.

    Examples
    --------
    >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8})
    Inventory: {'I-123': 399738.47946141585, 'Tc-99m': 71852.27235544211}, decay dataset: icrp107
    >>> H3 = rd.Radionuclide('H-3')
    >>> rd.Inventory({H3: 3.0})
    Inventory: {'H-3': 1682678687.3382246}, decay dataset: icrp107
    >>> rd.Inventory({'U-238': 21.1, 'Co-57': 7.2}, input_type="masses")
    Inventory: {'Co-57': 7.61542657764305e+22, 'U-238': 5.337817684684321e+22}, decay dataset: icrp107

    """

    def __init__(
        self,
        input: Dict[Union[str, Radionuclide], float],
        input_type: str = "activities",
        check: bool = True,
        data: DecayData = DEFAULTDATA
    ) -> None:

        self._change(input, input_type, check, data)

    def _change(
        self,
        contents: Dict[Union[str, Radionuclide], float],
        input_type: str,
        check: bool,
        data: DecayData
    ) -> None:
        """
        Changes the contents and data attributes of this Inventory instance.
        """

        parsed_contents: Dict[str, float] = _check_dictionary(
            contents, data.radionuclides, input_type, data
        ) if check is True else contents
        self.contents: Dict[str, float] = _sort_dictionary_alphabetically(
            parsed_contents
        )
        self.data: DecayData = data
        self.input_type = input_type
        
    @property
    def radionuclides(self) -> List[str]:
        """
        Returns a list of the radionuclides in the Inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).radionuclides
        ['I-123', 'Tc-99m']

        """

        return list(self.contents)
    
    def numbers(self) -> Dict[str, float]:
        """
        Returns a dictionary of radionuclides and associated numbers in the inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).numbers()
        {'I-123': 399738.47946141585, 'Tc-99m': 71852.27235544211}

        """

        return self.contents

    def activities(self) -> Dict[str, float]:
        """
        Returns a dictionary of radionuclides and associated activities in the inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).activities()
        {'I-123': 5.8, 'Tc-99m': 2.3}

        """

        activities = {
            nuc : _number_to_activity(nuc, num, self.data)
            for nuc, num in self.contents.items()
        }

        return activities
    
    def masses(self) -> Dict[str, float]:
        """
        Returns a dictionary of radionuclides and associated masses in the inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).masses()
        {'I-123': 8.158243973887584e-17, 'Tc-99m': 1.1800869622748501e-17}

        """

        masses = {
            nuc : _number_to_mass(nuc, num, self.data)
            for nuc, num in self.contents.items()
        }

        return masses
    
    def moles(self) -> Dict[str, float]:
        """
        Returns a dictionary of radionuclides and associated moles of material in the inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).moles()
        {'I-123': 6.637813617983513e-19, 'Tc-99m': 1.1931350531142702e-19}

        """

        moles = {
            nuc : _number_to_moles(num)
            for nuc, num in self.contents.items()
        }

        return moles
    
    def mass_abundances(self) -> Dict[str, float]:
        """
        Returns a dictionary of radionuclides and associated mass abundances in the inventory.

        Examples
        --------
        >>> rd.Inventory({'Tc-99m': 2.3, 'I-123': 5.8}).mass_abundances()
        {'I-123': 0.8736297770616593, 'Tc-99m': 0.12637022293834066}

        """

        total_mass = sum(self.masses().values())
        abundances = {
            nuc : mass / total_mass
            for nuc, mass in self.masses().items()
        }
        
        return abundances

    def __len__(self) -> int:
        """
        Returns number of radionuclides in the inventory.
        """

        return len(self.contents)

    def add(
        self,
        add_contents: Dict[Union[str, Radionuclide], float],
        input_type: str = "activity"
    ) -> None:
        """
        Adds a dictionary of radionuclides and associated numbers to the inventory.

        Parameters
        ----------
        add_contents : dict
            Dictionary containing radionuclide strings or Radionuclide objects as keys and
            activities as values which are added to the Inventory.
        input_type : str, optional
            Type of input, default is activities.

        Examples
        --------
        >>> inv = rd.Inventory({'H-3': 1.0}, "numbers")
        >>> inv.add({'C-14': 2.0}, "numbers")
        >>> inv.contents()
        {'C-14': 2.0, 'H-3': 1.0}

        """

        parsed_add_contents: Dict[str, float] = _check_dictionary(
            add_contents, self.data.radionuclides, input_type, self.data
        )
        new_contents = _add_dictionaries(self.contents, parsed_add_contents)
        self._change(new_contents, "numbers", False, self.data)

    def subtract(
        self,
        sub_contents: Dict[Union[str, Radionuclide], float],
        input_type: str = "activities"
    ) -> None:
        """
        Subtracts a dictionary of radionuclides and associated numbers from this inventory.

        Parameters
        ----------
        sub_contents : dict
            Dictionary containing radionuclide strings or Radionuclide objects as keys and
            numbers as values which are subtracted from the Inventory.

        Examples
        --------
        >>> inv = rd.Inventory({'C-14': 2.0, 'H-3': 1.0}, "numbers")
        >>> inv.subtract({'H-3': 1.0}, "numbers")
        >>> inv.contents()
        {'C-14': 2.0, 'H-3': 0.0}

        """
        parsed_sub_contents: Dict[str, float] = _check_dictionary(
            sub_contents, self.data.radionuclides, input_type, self.data
        )
        parsed_sub_contents.update(
            (nuclide, number * -1.0)
            for nuclide, number in parsed_sub_contents.items()
        )
        new_contents = _add_dictionaries(self.contents, parsed_sub_contents)
        self._change(new_contents, "numbers", False, self.data)

    def __add__(self, other: "Inventory") -> "Inventory":
        """
        Defines + operator to add two Inventory objects together.
        """

        if self.data.dataset != other.data.dataset:
            raise ValueError(
                "Decay datasets do not match. inv1: "
                + self.data.dataset
                + " inv2: "
                + other.data.dataset
            )
        new_contents = _add_dictionaries(self.contents, other.contents)
        return Inventory(new_contents, "numbers", False, self.data)

    def __sub__(self, other: "Inventory") -> "Inventory":
        """
        Defines - operator to subtract one Inventory object from another.
        """

        if self.data.dataset != other.data.dataset:
            raise ValueError(
                "Decay datasets do not match. inv1: "
                + self.data.dataset
                + " inv2: "
                + other.data.dataset
            )
        sub_contents = other.contents.copy()
        sub_contents.update(
            (nuclide, number * -1.0)
            for nuclide, number in sub_contents.items()
        )
        new_contents = _add_dictionaries(self.contents, sub_contents)
        return Inventory(new_contents, "numbers", False, self.data)

    def __mul__(self, const: float) -> "Inventory":
        """
        Defines * operator to multiply all activities of radionuclides in an Inventory by a
        float or int.
        """

        new_contents = self.contents.copy()
        for nuclide, number in new_contents.items():
            new_contents[nuclide] = number * const
        return Inventory(new_contents, "numbers", False, self.data)

    def __rmul__(self, const: float) -> "Inventory":
        """
        Defines * operator to multiply all activities of radionuclides in an Inventory by a
        float or int.
        """

        return self.__mul__(const)

    def __truediv__(self, const: float) -> "Inventory":
        """
        Defines / operator to divide all activities of radionuclides in an Inventory by a
        float or int.
        """

        return self.__mul__(1.0 / const)

    @_method_dispatch
    def remove(
        self, delete: Union[str, Radionuclide, List[Union[str, Radionuclide]]]
    ) -> None:
        """
        Removes radionuclide(s) from this inventory.

        Parameters
        ----------
        delete : str or Radionuclide or list
            Radionuclide string, Radionuclide object or list of radionuclide strings or
            Radionuclide objects to delete from the Inventory object.

        Examples
        --------
        >>> inv = rd.Inventory({'Be-10': 2.0, 'C-14': 3.0, 'H-3': 1.0, 'K-40': 4.0})
        >>> inv.remove('H-3')
        >>> inv.activities()
        {'Be-10': 2.0, 'C-14': 3.0, 'K-40': 4.0}
        >>> inv.remove(['Be-10', 'K-40'])
        >>> inv.activities()
        {'C-14': 3.0}

        """
        raise NotImplementedError("remove() takes string or list of radionuclides.")

    @remove.register(str)
    def _(self, delete: str) -> Callable[[Dict[str, float], bool, DecayData], None]:
        """Remove radionuclide string from this inventory."""

        delete = parse_radionuclide(delete, self.data.radionuclides, self.data.dataset)
        new_contents = self.contents.copy()
        if delete not in new_contents:
            raise ValueError(delete + " does not exist in this inventory.")
        new_contents.pop(delete)
        self._change(new_contents, "numbers", False, self.data)

    @remove.register(Radionuclide)
    def _(
        self, delete: Radionuclide
    ) -> Callable[[Dict[str, float], bool, DecayData], None]:
        """Remove radionuclide object from this inventory."""

        delete = parse_radionuclide(
            delete.radionuclide, self.data.radionuclides, self.data.dataset
        )
        new_contents = self.contents.copy()
        if delete not in new_contents:
            raise ValueError(delete + " does not exist in this inventory.")
        new_contents.pop(delete)
        self._change(new_contents, "numbers", False, self.data)

    @remove.register(list)
    def _(
        self, delete: List[Union[str, Radionuclide]]
    ) -> Callable[[Dict[str, float], bool, DecayData], None]:
        """Remove list of radionuclide(s) from this inventory."""

        delete = [
            parse_radionuclide(
                nuc.radionuclide, self.data.radionuclides, self.data.dataset
            )
            if isinstance(nuc, Radionuclide)
            else parse_radionuclide(nuc, self.data.radionuclides, self.data.dataset)
            for nuc in delete
        ]
        new_contents = self.contents.copy()
        for nuc in delete:
            if nuc not in new_contents:
                raise ValueError(nuc + " does not exist in this inventory.")
            new_contents.pop(nuc)
        self._change(new_contents, "numbers", False, self.data)

    def decay(
        self, decay_time: float, units: str = "s", sig_fig: Union[None, int] = None
    ) -> "Inventory":
        """
        Returns a new Inventory calculated from the radioactive decay of the current Inventory for
        decay_time.

        Parameters
        ----------
        decay_time : float
            Decay time.
        units : str, optional
            Units of decay_time (default is seconds). Options are 'ns', 'us', 'ms', 's', 'm', 'h',
            'd', 'y', 'ky', 'My', 'Gy', 'Ty', 'Py', and some of the common spelling variations of
            these time units.
        sig_fig: None or int, optional
            Performs a decay calculation using arbitrary-precision arithmetic with SymPy for this
            many significant figures. For high precision calculations, recommended setting is 320.
            sig_fig must be greater than 0. Default is None, which is standard SciPy/NumPy double
            precision calculations.

        Returns
        -------
        Inventory
            New Inventory after the radioactive decay.

        Raises
        ------
        ValueError
            If sig_fig is invalid or if the decay dataset associated with this Inventory
            (self.data) does not contain SymPy versions of the decay data.

        Examples
        --------
        >>> inv_t0 = rd.Inventory({'H-3': 1.0})
        >>> inv_t1 = inv_t0.decay(12.32, 'y')
        >>> inv_t1.activities()
        {'H-3': 0.5, 'He-3': 0.0}

        """

        if sig_fig is not None:
            if sig_fig < 1:
                raise ValueError("sig_fig needs to be an integer greater than 0.")
            if self.data.sympy_data is None:
                raise ValueError("No SymPy data in decay dataset " + self.data.dataset)
            return self._decay_sympy(decay_time, units, sig_fig)

        decay_time = (
            decay_time
            if units == "s"
            else time_unit_conv(
                decay_time,
                units_from=units,
                units_to="s",
                year_conv=self.data.scipy_data.year_conv,
            )
        )

        vector_n0 = self.data.scipy_data.vector_n0.copy()
        indices_set = set()
        for radionuclide in self.contents:
            i = self.data.radionuclide_dict[radionuclide]
            vector_n0[i] = (self.contents[radionuclide])
            indices_set.update(self.data.scipy_data.matrix_c[:, i].nonzero()[0])
        indices = list(indices_set)

        matrix_e = self.data.scipy_data.matrix_e.copy()
        matrix_e.data[indices] = np.exp(
            -decay_time * self.data.scipy_data.decay_consts[indices]
        )

        vector_nt = (
            self.data.scipy_data.matrix_c
            @ matrix_e
            @ self.data.scipy_data.matrix_c_inv
            @ vector_n0
        )
        vector_at = vector_nt[indices]

        new_contents = _sort_dictionary_alphabetically(
            dict(zip(self.data.radionuclides[indices], vector_at))
        )

        return Inventory(new_contents, "numbers", False, self.data)

    def decay_high_precision(
        self, decay_time: float, units: str = "s", sig_fig: int = 320
    ) -> "Inventory":
        """
        Decay calculation with high numerical precision. This uses SymPy arbitrary-precision
        arithmetic functions for the decay calculation. The results can be more accurate than
        a normal double precision float calculation (i.e. using ``decay(..., sig_fig=None)``) when
        the decay chains contain radionuclides with very similar half-lives or half-lives that
        differ by many orders of magnitude.

        This function requires that the decay dataset associated with the Inventory instance
        contains a SymPy version of the decay data. Default is sig_fig=320 for the SymPy
        calculation.

        Parameters
        ----------
        decay_time : float
            Decay time.
        units : str, optional
            Units of decay_time (default is seconds). Options are 'ns', 'us', 'ms', 's', 'm', 'h',
            'd', 'y', 'ky', 'My', 'Gy', 'Ty', 'Py', and some of the common spelling variations of
            these time units.
        sig_fig: int, optional
            Number of significant figures for high precision decay calculation. Deafult is 320.

        Returns
        -------
        Inventory
            New Inventory after the radioactive decay.
        
        Examples
        --------
        >>> inv_t0 = rd.Inventory({'Fm-257': 1.0})
        >>> inv_t1 = inv_t0.decay_high_precision(10.0, 'd')
        >>> inv_t1.activities()
        {'Ac-225': 4.080588235484085e-50,
        'Am-241': 6.3571164015402466e-27,
        'Am-245': 6.3608186478274594e-06,
        ...
        'Fm-257': 0.9333548028364756,
        ...
        }
        """

        return self.decay(decay_time, units, sig_fig)

    def _decay_sympy(self, decay_time: float, units: str, sig_fig: int) -> "Inventory":
        """
        Version of decay() using SymPy arbitrary-precision arithmetic.
        """

        decay_time = nsimplify(decay_time)

        decay_time = (
            decay_time
            if units == "s"
            else time_unit_conv_sympy(
                decay_time,
                units_from=units,
                units_to="s",
                year_conv=self.data.sympy_data.year_conv,
            )
        )

        vector_n0 = self.data.sympy_data.vector_n0.copy()
        indices_set = set()
        for radionuclide in self.contents:
            i = self.data.radionuclide_dict[radionuclide]
            vector_n0[i, 0] = (nsimplify(self.contents[radionuclide]))
            indices_set.update(self.data.scipy_data.matrix_c[:, i].nonzero()[0])
        indices = list(indices_set)

        matrix_e = self.data.sympy_data.matrix_e.copy()
        for i in indices:
            matrix_e[i, i] = exp(
                (-decay_time * self.data.sympy_data.decay_consts[i, 0]).evalf(sig_fig)
            )

        vector_nt = (
            self.data.sympy_data.matrix_c
            @ matrix_e
            @ self.data.sympy_data.matrix_c_inv
            @ vector_n0
        )

        new_contents = {}
        for i in indices:
            new_contents[self.data.radionuclides[i]] = float(vector_nt[i, 0])
        new_contents = _sort_dictionary_alphabetically(new_contents)

        return Inventory(new_contents, "numbers", False, self.data)

    def half_lives(self, units: str = "s") -> Dict[str, Union[float, str]]:
        """
        Returns dictionary of half-lives of the radionuclides in the Inventory in your chosen time
        units, or as a human-readable string with appropriate units.

        Parameters
        ----------
        units : str, optional
            Units for half-life. Options are 'ps', 'ns', 'μs', 'us', 'ms', 's', 'm', 'h', 'd', 'y',
            'ky', 'My', 'By', 'Gy', 'Ty', 'Py', and common spelling variations. Default is 's', i.e.
            seconds. Use 'readable' to get strings of the half-lives in human-readable units.

        Returns
        -------
        dict
            Dictionary with radionuclide strings as keys and half-life floats or human-readable
            half-life strings as values.

        Examples
        --------
        >>> inv = rd.Inventory({'C-14': 1.0, 'K-40': 2.0})
        >>> inv.half_lives('y')
        {'C-14': 5700.0, 'K-40': 1251000000.0}

        """

        return {nuc: self.data.half_life(nuc, units) for nuc in self.contents}

    def half_life(self, units: str = "s") -> Dict[str, Union[float, str]]:
        """
        Same behaviour as half_lives() method.
        """

        return self.half_lives(units)

    def progeny(self) -> Dict[str, List[str]]:
        """
        Returns dictionary with the direct progeny of the radionuclides in the Inventory.

        Returns
        -------
        dict
            Dictionary with radionuclide strings as keys and lists of the direct progeny of each
            radionuclide, ordered by decreasing branching fraction, as values.

        Examples
        --------
        >>> inv = rd.Inventory({'C-14': 1.0, 'K-40': 2.0})
        >>> inv.progeny()
        {'C-14': ['N-14'], 'K-40': ['Ca-40', 'Ar-40'])

        """

        return {nuc: Radionuclide(nuc, self.data).progeny() for nuc in self.contents}

    def branching_fractions(self) -> Dict[str, List[float]]:
        """
        Returns dictionary with the branching fractions of the direct progeny of the radionuclides
        in the Inventory.

        Returns
        -------
        dict
            Dictionary with radionuclide strings as keys and lists of the branching fractions to
            the direct progeny of each radionuclide as values.

        Examples
        --------
        >>> inv = rd.Inventory({'C-14': 1.0, 'K-40': 2.0})
        >>> inv.branching_fractions()
        {'C-14': [1.0], 'K-40': [0.8914, 0.1086])

        """

        return {
            nuc: Radionuclide(nuc, self.data).branching_fractions()
            for nuc in self.contents
        }

    def decay_modes(self) -> Dict[str, List[str]]:
        """
        Returns dictionary with the decay modes of the direct progeny of the radionuclides in the
        Inventory. Note: the decay mode strings returned are not lists of all the different
        radiation types emitted during the parent to progeny decay processes. They are the labels
        defined in the decay dataset to classify the decay type (e.g. '\u03b1', '\u03b2-' or 'IT').

        Returns
        -------
        dict
            Dictionary with radionuclide strings as keys and lists of the decay modes of the parent
            radionuclide

        Examples
        --------
        >>> inv = rd.Inventory({'C-14': 1.0, 'K-40': 2.0})
        >>> inv.decay_modes()
        {'C-14': ['\u03b2-'], 'K-40': ['\u03b2-', '\u03b2+ \u0026 EC'])

        """

        return {
            nuc: Radionuclide(nuc, self.data).decay_modes() for nuc in self.contents
        }

    def plot(
        self,
        xmax: float,
        xunits: str = "s",
        xmin: float = 0.0,
        xscale: str = "linear",
        yscale: str = "linear",
        ymin: float = 0.0,
        ymax: Union[None, float] = None,
        yunits: Union[None, str] = None,
        sig_fig: Union[None, int] = None,
        display: Union[str, List[str]] = "all",
        order: str = "dataset",
        npoints: Union[None, int] = None,
        fig: Union[None, matplotlib.figure.Figure] = None,
        ax: Union[None, matplotlib.axes.Axes] = None,
        **kwargs,
    ) -> Tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        """
        Plots a decay graph showing the change in activity of the inventory over time. Creates
        matplotlib fig, ax objects if they are not supplied. Returns fig, ax tuple.

        Parameters
        ----------
        xmax : float
            Maximum decay time on x-axis.
        xunits : str, optional
            Units for decay times (default is 's', i.e. seconds). Options are 'ps', 'ns', 'us',
            'ms', 's', 'm', 'h', 'd', 'y', 'ky', 'My', 'Gy', 'Ty', 'Py', and some of the common
            spelling variations of these time units.
        xmin : float, optional
            Minimum decay time on x-axis (default is 0.0 for linear x-axis, 0.1 for log x-axis).
        xscale : str, optional
            The time axis scale type to apply ('linear' or 'log', default is 'linear').
        yscale : str, optional
            The activities axis scale type to apply ('linear' or 'log', default is 'linear').
        ymin : float, optional
            Minimum activity for the y-axis (default is 0.0 for linear y-axis, 0.1 for log y-axis).
        ymax : None or float, optional
            Maximum activity for the y-axis. Default is None, which sets the limit to 1.05x the
            maximum radioactivity that occurs over the decay period.
        yunits : None or str, optional
            Acivity unit for the y-axis label (default is to show no unit).
        sig_fig : None or int, optional
            None: use normal double precision decay calculations (default), int: perform Sympy high
            precision decay calculations with this many significant figures.
        display : str or list, optional
            Only display the radionuclides within this list on the graph. Use this parameter when
            you want to choose specific radionuclide decay curves shown on the graph, either by
            supplying a string (to show one radionuclide) or a list of strings (to show multiple).
            Default is 'all', which displays all radionuclides present upon decay of the inventory.
        order : str, optional
            Order to display the radionuclide decay curves on the graph if you do not specify the
            order via the display parameter. Default order is by "dataset", which follows the order
            of the radionuclides in the decay dataset (highest to lowest radionuclides in the decay
            chains). Use "alphabetical" if you want the radionuclides to be ordered alphabetically.
        npoints : None or int, optional
            Number of time points used to plot graph (default is 501 for normal precision decay
            calculations, or 51 for high precision decay calculations (sig_fig > 0)).
        fig : None or matplotlib.figure.Figure, optional
            matplotlib figure object to use, or None makes ``radioactivedecay`` create one (default
            is None).
        ax : None or matplotlib.axes.Axes, optional
            matplotlib axes object to use, or None makes ``radioactivedecay`` create one (default
            is None).
        **kwargs, optional
            All additional keyword arguments to supply to matplotlib plot() function.

        Returns
        -------
        fig : matplotlib.figure.Figure
            matplotlib figure object used to plot decay chain.
        ax : matplotlib.axes.Axes
            matplotlib axes object used to plot decay chain.

        Raises
        ------
        ValueError
            If the order parameter is invalid.

        """

        if npoints is None:
            if sig_fig:
                npoints = 51
            else:
                npoints = 501

        if xscale == "linear":
            time_points = np.linspace(xmin, xmax, num=npoints)
        else:
            if xmin == 0.0:
                xmin = 0.1
            time_points = np.logspace(np.log10(xmin), np.log10(xmax), num=npoints)

        if display == "all":
            if order == "dataset":
                display = _sort_list_according_to_dataset(
                    self.decay(0).radionuclides, self.data.radionuclide_dict
                )
            elif order == "alphabetical":
                display = self.decay(0).radionuclides
            else:
                raise ValueError(
                    str(order) + " is not a valid string for the order parameter."
                )
        else:
            if isinstance(display, str):
                display = [display]
            display = [
                parse_radionuclide(rad, self.data.radionuclides, self.data.dataset)
                for rad in display
            ]

        acts = np.zeros(shape=(npoints, len(display)))
        for i in range(0, npoints):
            decayed_contents = self.decay(time_points[i], xunits, sig_fig).contents
            acts[i] = [decayed_contents[rad] for rad in display]

        if yscale == "log" and ymin == 0.0:
            ymin = 0.1
        ylimits = [ymin, ymax] if ymax else [ymin, 1.05 * acts.max()]

        fig, ax = _decay_graph(
            time_points=time_points,
            activities=acts.T,
            radionuclides=display,
            xunits=xunits,
            yunits=yunits,
            xscale=xscale,
            yscale=yscale,
            ylimits=ylimits,
            display=set(display),
            fig_in=fig,
            ax_in=ax,
            **kwargs,
        )

        return fig, ax

    def __repr__(self) -> str:
        return (
            "Inventory: " + str(self.contents) + ", decay dataset: " + self.data.dataset
        )

    def __eq__(self, other) -> bool:
        """
        Check whether two ``Inventory`` instances are equal with ``==`` operator.
        """

        return self.contents == other.contents and self.data == other.data

    def __ne__(self, other) -> bool:
        """
        Check whether two ``Inventory`` instances are not equal with ``!=`` operator.
        """

        return not self.__eq__(other)
