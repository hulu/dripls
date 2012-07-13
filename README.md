Summary
==========

DripLS - Make a CDN in a box service that is able to perform traffic shaping for testing purposes on a http live stream.

Usage
==========

	http://dripls-host/cache?authkey=[authkey]&cid=[cid]&tag=[tag]&r=[rules]

Prepare a traffic shaped playlist and return its streamable url on completion along with segments which were rule matched (along with their matched url). The cache request is synchronous. The call will return when the matching segments and vplaylists are cached and traffic shaped. Use /cache, to avoid re-generating the same playlist with the same rules over and over again.

	http://dripls-host/master.m3u8?authkey=[authkey]&cid=[cid]&tag=[tag]&r=[rules]

Returns back an actual streamable m3u8 playlist. master.m3u8 calls cache internally, so this call is inherently synchronous. It will return the master playlist as soon as the playlist traffic shaping is done. This is useful for feeding this url directly to m3u8 players to achieve the effect of on-the-fly traffic shaping, while still serving a playable playlist back. For example directly feeding a master.m3u8 to a device player, should still result in the device playing the video stream properly.

	http://dripls-host/tag.m3u8?authkey=[authkey]&tag=[tag]

Returns back a streamable m3u8 playlist, previously prepared via a call to /master.m3u8 or /cache with a tag argument. When the call to master.m3u8 or cache was made, all url arguments(except authkey) have gotten stored locally under tag tag. tag.m3u8 uses the previously specified query arguments in the current shaping call. The main purpose of tag.m3u8 is to reduce the complexity and provide aliasing for complex rule sets. Additional arguments, such as cid, r, can be specified to override the arguments previously specified.

	http://dripls-host/updatesegment?authkey=[authkey]&url=[previously_shaped_url|previously_shaped_url]&new_action=[rule_action|rule_action]

Re-shapes a segment, specified by previously\_shaped\_url. The previously\_shaped\_url is retrieved via call to /cache, which performs the initial shape. The new_action is the action portion of a rule ( ex. net100.loss10) . Note that the segment MUST be previously shaped with a net rule in order to be reshaped. Segments that are matched by the e(rror) rule cannot be re-shaped, due to the fact that a playlist structure change must occur, which could lead to the possibility of inconsistent results due to client content caching. Re-shaping via /updatesegment is virtually transparent to the client, and can occur in-flight during streaming. During re-shaping only the actual segment shaping rules (on the server) are changed, while the actual playlist is not modified.

	http://dripls-host/master.m3u8?authkey=[authkey]&cid=url&cid_url=[url-to-original-master-m3u8]&tag=[tag]&r=[rules]

DripLS supports fetching and reshaping from an already accessible master m3u8. This is supported with all endpoints ( master.m3u8, cache, tag.m3u8). This configuration is useful when you already have a pre-built m3u8 available online ( either on a CDN, or another host accessible by the DripLS node) and you want to use DripLS to traffic shape this m3u8. To use this configuration set the cid parameter value to url and provide an additional parameter cid_url, which points to your master m3u8.

Parameter Details
==========


__authkey__ - authentication key to protect the service from distributing content to unauthorized users

__cid__ - content id ( default package supports cid=wt , which is test video)

__tag__ - can be specified while calling /master.m3u8 or /cache to allow later re-invocation of the rules + cid url via /tag.m3u8

__r__ - rules to transform the httpls m3u8 files, comma separated, format rule~action. For more detailed information see the Rules section


Rule Format
==========

Each rule has the following format: rule-match-expresison~action.

Rule Match Expression
===============

Each rule expression is in the format optional cdn.bitrate.optional segment. All parts of the expression support wild-cards. When a rule expression matches a segment, then the action associated with the expression is applied to the segment itself.

For example, 650k.s0 as a rule match expression would match the first segment of the 650kbit playlist and apply the action part to that segment. Similarly, .s0 would apply the action for the first segment of all variable playlists, and v.650k.s would match all segments in the 650kbit playlist for cdn V.

If the segment part of the expression is missing, the assumption is that the rule action is to be applied to the variant playlist, as opposed to its segment(s). For example a rule like 650k~e404, would translate to the master m3u8 playlist having a 404 link for its 650kbit playlist.

Here are the available options for each rule expression:

CDN
===============


 __cdn__ - specifies the cdn from which the serving is happening. The cdn is extracted from the url and can be arbitrarily configured as needed. Current Hulu CDNs are limited to : a,v ( ex v.650k~e404, would translate to the 650kbit playlist on the v cdn having all of its segments replaced with 404 page references)

 __*none*__ - cdn can be ommited in the expression, which would be interpreted as meaning from "any" cdn

Bitrate
===============


__[bitrate]k__  - specifies the bit rate of the playlist for which the rule expression is for (ex. 650k , 1000k, 1500k) 

__[bitrate]-[bitrate]k__  - specifies the bit rate range of the playlists for which the rule expression is for (ex. 650-3000k , 400-1000k) 

__\*__           - wild-card can be used to mean "any" bit-rate playlist

Segment
===============
__s[number]__   - Specifies the absolute(regardless of type) segment number within the variable 
                  playlist for which the rule expression is for (ex. s0 - first segment, s1 - 
                  second segm ent, s2 - third segment) .

__s\*__	        - Wild-card can be used to mean "any" segment within the playlist 

__s[num]-[num]__ - Range can be used to mean "any" segment within the range of the playlist ( ex s0-5, s10-30)

__c[number]__	- Specifies the content ( not ad or pre-roll) segment number within the variable 
                  playlist for which the rule expression is for (ex. c0 - first content segment after ads/pre-rolls) 

__c\*__	        - Wild-card can be used to mean "any" content( not ad or pre-roll ) segment within the playlist 

__c[num]-[num]__ - Range can be used to mean "any" segment within the range of the playlist ( ex c0-5, c10-30)

__a[number]__   - Specifies the ad segment number within the variable playlist for which the rule expression
                  is for (ex. a0 - first ad segment)

__a*__	        - Wild-card can be used to mean "any" ad segment within the playlist 

__a[num]-[num]__ - Range can be used to mean "any" segment within the range of the playlist ( ex a0-5, a10-30)

Note: *s* above denotes any segment in an ascending order. *c*, *a* and other segment types are configurable via the data provider in conf/data.py. 

Rule Action
==============
This is the action to be applied to a segment or playlist, when a matching rule is found for it:

Action
==================
__e[http error code]__                                - Replace the playlist's matching segment url with a url that returns a 404 status code upon invocation ( ex. e404 ) 

__net[bandwidth in kbit]loss[% of packets dropped]__  - The net rule action, when applied to a segment, causes the segment to be stream served at 
                                                        [bandwidth in kbit]  with [% of packets dropped]  ( ex. net200loss10 - serve the matched segment at 200kbit
                                                        max with 10% packet loss during transmission)

__netcache[bandwidth in kbit]loss[% of packets dropped]__  - The netcache rule action, when applied to a segment, causes the segment to be locally cached and then served at 
                                                        [bandwidth in kbit]  with [% of packets dropped]  ( ex. netcache200loss10 - serve the matched segment at 200kbit
                                                        max with 10% packet loss during transmission)


Master Playlist Fetching and Options
==================

Content fetching is piped to the original m3u8 provider. As such the original provider might request or offer additional optional functionality.

Local (wt)
======================
The local test ( world travel) video does not offer additional features at that time.

Custom 
======================
Custom url parameters can be passed in the url line, and they will be forwarded to the original m3u8 server for correct fetching of the content. Examples can include specifying multiple cdns, additional authentication parameters, device ids , etc. 

Auth Key
======================
use authkey=sample for cid=wt ( for world travel local sample video)

authkey is not required, but is recommended to provide simple protection to the service

Some Examples
======================
Replace dripls-host with the appropriate dripls instance

Variant playlist has first segment that 404s

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=650k.s0~e404 

>Fail first segment on 650k playlist (usually an asset segment, switch to c0 for first content segment) with 404


Variant playlist has middle segment that 404s

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=650k.s20~e404 

>Fail segment 20 on 650k playlist with 404


Variant playlist has several consecutive segments that 404

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=650k.s1~e404,650k.s2~e404,650k.s3~e404,650k.s4~e404

>Fail segments 1-4 on the 650k playlist with 404


Master playlist has variant playlist that 404s

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=650k~e404

>650k playlist 404s in master playlist


Multiple variant playlists 404 on the same segment

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.s0~e404

>Fail first segment on all variant playlists

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=650k.s0~e404,1000k.s0~e500 

>Fail first segment 404 on 650k and 500 on the 1000k variant playlist

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.s12~e404,*.s13~e404

>Fail two consecutive segments on all variant playlists

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.c0~e404

>Fail first content segment (after assets/pre-roll ads)


Traffic shape segments

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.c1~net5 

>The second content segment of each playlist, and rewrite the vplaylist to serve the segment with maximum download speed of 5kbs

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.c2~net500.loss10

>The hird content segment of each playlist, and rewrite the vplaylist to serve the segment with maximum download speed of 500kbs and 10% packet loss

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=*.c1~net5,*.c2~net500.loss10

>Combine the above two traffic shaping rules


CDN Specific targeting

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=a.650k.s*~e404 
>For the 650kbit playlist coming from CDN 'a' , transform all segment urls to 404 error message urls

       http://dripls-host/master.m3u8?authkey=sample&cid=wt&r=a.*.s1~e404 
>For the second segment in all variant playlists coming from CDN 'a' , transform their urls to to 404 error messages


Some Cache/Reshape Examples
======================

Initial shape

      http://dripls-host/cache?authkey=sample&cid=wt&r=4000k.s2~net10 

>Perform the initial shape, streaming s2 at 10kbs . Result would return small JSON object for example:
>Output: { "4000000._d.s2": "http://dripls-host/s/10001/ts.ts?s=e92cc3a7270d48c34398ad894a83d34fb23d9741a01cc16c20290bb8", 
>    "id": "wt_bfb7c6b6d16141128545aed48bddc93a", "url": "http://dripls-host/playlist.m3u8?p=m_wt_bfb7c6b6d16141128545aed48bddc93a" }

>The 4000k segment 2 has been shaped to : http://dripls-host/s/10001/ts.ts?s=e92cc3a7270d48c34398ad894a83d34fb23d9741a01cc16c20290bb8

Re-shape

      http://dripls-host/updatesegment?authkey=sample&url=http://dripls-host/s/10001/ts.ts?s=e92cc3a7270d48c34398ad894a83d34fb23d9741a01cc16c20290bb8&new_action=net1000

>Now the segment s2 would continue to be streamed at 1000kbs

License
==========
Copyright (C) 2010-2011 by Hulu, LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Contact
==========

For support or for further questions, please contact:

      dripls-dev@googlegroups.com


