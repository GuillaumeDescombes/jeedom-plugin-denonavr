/* This file is part of Jeedom.
*
* Jeedom is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
*/


jeedom.denonavr = function() {};

jeedom.denonavr.getDescription = function(_params){
  var paramsRequired = ['ip'];
  var paramsSpecifics = {};
  try {
    jeedom.private.checkParamsRequired(_params || {}, paramsRequired);
  } catch (e) {
    (_params.error || paramsSpecifics.error || jeedom.private.default_params.error)(e);
    return;
  }
  var params = $.extend({}, jeedom.private.default_params, paramsSpecifics, _params || {});
  var paramsAJAX = jeedom.private.getParamsAJAX(params);
  paramsAJAX.url = 'plugins/denonavr/core/ajax/denonavr.ajax.php';
  paramsAJAX.data = {
    action: 'getSSDPDescription',
    ip : _params.ip,
  };
  console.log(paramsAJAX);
  $.ajax(paramsAJAX);
}

jeedom.denonavr.createCommands = function(_params){
  var paramsRequired = ['id'];
  var paramsSpecifics = {};
  try {
    jeedom.private.checkParamsRequired(_params || {}, paramsRequired);
  } catch (e) {
    (_params.error || paramsSpecifics.error || jeedom.private.default_params.error)(e);
    return;
  }
  var params = $.extend({}, jeedom.private.default_params, paramsSpecifics, _params || {});
  var paramsAJAX = jeedom.private.getParamsAJAX(params);
  paramsAJAX.url = 'plugins/denonavr/core/ajax/denonavr.ajax.php';
  paramsAJAX.data = {
    action: 'createCommands',
    removeexistingcommands: 1,
    id : _params.id,
  };
  console.log(paramsAJAX);
  $.ajax(paramsAJAX);
}
