import os
import sys
from io import TextIOBase

#
# This module is heavily based on Django, adapted from functionality found in
# ``django.core.management.base``, ``django.core.management.color``, and
# ``django.utils.termcolors``.
#

COLOR_NAMES = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
FOREGROUND = {COLOR_NAMES[x]: '3%s' % x for x in range(8)}
BACKGROUND = {COLOR_NAMES[x]: '4%s' % x for x in range(8)}

OPTIONS = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}
RESET = '\x1b[0m'


class Styler:
    """
    An object containing methods for generating styled text for a palette of
    preconfigured style roles. Text is styled by wrapping it in appropriate
    ANSI graphics codes.
    
    Text styling can be disabled using the ``no_color`` constructor argument.
    When ``True``, all methods will return the provided text unmodified. This
    enables a common API between environments that support styled text and
    those that do not.
    
    :attr:`~Styler.PALETTE` defines the name and attributes of each
    preconfigured role. Its entries are mapped into methods on the class that
    can be used as shortcuts to apply the corresponding set of style attributes
    to the given text. Subclasses can define their own palettes.
    
    Additionally, the :meth:`~Styler.apply` method can be used to apply any
    arbitrary text styles if the :attr:`~Styler.PALETTE` configuration doesn't
    include a suitable role.
    
    Usage::
    
        styler = Styler()
        success_message = styler.success('It worked!')
        error_message = styler.error('It failed!')
        message = styler.apply('hello', fg='red', bg='blue', opts=('blink', ))
    """
    
    PALETTE = {
        'normal': {},
        'success': {'fg': 'green', 'options': ('bold', )},
        'error': {'fg': 'red', 'options': ('bold', )},
        'warning': {'fg': 'yellow', 'options': ('bold', )},
        'info': {'options': ('bold', )},
        'debug': {'fg': 'magenta', 'options': ('bold', )},
        'heading': {'fg': 'cyan', 'options': ('bold', )},
        'label': {'options': ('bold', )},
    }
    
    def __init__(self, no_color=False):
        
        self.no_color = no_color
        
        for role, fmt in self.PALETTE.items():
            setattr(self, role, self.preconfigure(**fmt))
    
    def preconfigure(self, **kwargs):
        """
        Return a function with default parameters for ``apply()``.
        
        Examples::
            
            bold_red = styler.preconfigure(opts=('bold',), fg='red')
            print(bold_red('hello'))
            
            KEYWORD = styler.preconfigure(fg='yellow')
            COMMENT = styler.preconfigure(fg='blue', opts=('bold',))
        """
        
        return lambda text: self.apply(text, **kwargs)
    
    def apply(self, text, fg=None, bg=None, options=(), reset=True):
        """
        Return ``text``, enclosed in ANSI graphics codes, as dictated by
        ``fg``, ``bg``, and ``options``. If ``reset`` is ``True``, the returned
        text will be terminated by the RESET code.
        
        If configured with ``no_color=True``, return the text unmodified.
        
        Valid colors::
        
            'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        
        Valid options::
        
            'bold', 'underscore', 'blink', 'reverse', 'conceal'
        
        Examples::
            
            styler.apply('hello', fg='red', bg='blue', opts=('blink', ))
            styler.apply('goodbye', opts=('underscore', ))
            print(styler.apply('first line', fg='red', reset=False))
            print('this should be red too')
            print(styler.apply('and so should this'))
            print('this should not be red')
        
        :param text: The text to style.
        :param fg: The foreground colour to apply to ``text``.
        :param bg: The background colour to apply to ``text``.
        :param options: The display options to apply to ``text``.
        :param reset: ``True`` to clear all applied styles at the end of ``text``,
            ``False`` to allow them to affect subsequent output.
        :return: The styled text.
        """
        
        if self.no_color:
            return text
        
        if reset:
            text = f'{text}{RESET}'
        
        code_list = []
        
        if fg:
            code_list.append(FOREGROUND[fg])
        
        if bg:
            code_list.append(BACKGROUND[bg])
        
        for o in options:
            code_list.append(OPTIONS[o])
        
        if code_list:
            code_list = ';'.join(code_list)
            text = f'\x1b[{code_list}m{text}'
        
        return text
    
    def reset(self):
        """
        Return the ANSI RESET graphics code. Can be used to reset a style
        created by calling ``apply(..., reset=False)``.
        
        If configured with ``no_color=True``, return an empty string.
        
        :return: The ANSI RESET graphics code.
        """
        
        if self.no_color:
            return ''
        
        return RESET


class OutputWrapper(TextIOBase):
    """
    Simple wrapper around ``stdout``/``stderr`` to normalise some behaviours.
    """
    
    def __init__(self, out, default_style=None, no_color=False):
        
        self._out = out
        
        no_color = no_color or not self.supports_color()
        self.styler = Styler(no_color)
        self.default_style = default_style
    
    def __getattr__(self, name):
        
        return getattr(self._out, name)
    
    def supports_color(self):
        """
        Return True if the output stream supports color, and False otherwise.
        """
        
        plat = sys.platform
        supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
        is_a_tty = hasattr(self._out, 'isatty') and self._out.isatty()
        
        return supported_platform and is_a_tty
    
    def write(self, msg, style=None, ending='\n'):
        
        if ending:
            msg += ending
        
        style = style or self.default_style
        if style:
            msg = getattr(self.styler, style)(msg)
        
        self._out.write(msg)
