
package org.sasanlabs.service.vulnerability.xss.reflected;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestParam;

@VulnerableAppRestController(descriptionLabel = "XSS_VULNERABILITY", value = "XSSInImgTagAttribute")
public class XSSInImgTagAttribute {

    @VulnerableAppRequestMapping(
            value = LevelConstants.LEVEL_7,
            variant = Variant.SECURE,
            htmlTemplate = "LEVEL_1/XSS")
    public ResponseEntity<String> getVulnerablePayloadLevelSecure3(
            @RequestParam(PARAMETER_NAME) String imageLocation) {
        String vulnerablePayloadWithPlaceHolder = "<img src=\"%s\" width=\"400\" height=\"300\"/>";

        if ((imageLocation.startsWith(IMAGE_RESOURCE_PATH)
                        && imageLocation.endsWith(FILE_EXTENSION))
                || allowedValues.contains(imageLocation)) {

            String payload =
                    String.format(
                            vulnerablePayloadWithPlaceHolder,
                            HtmlUtils.htmlEscapeHex(imageLocation));

            return ResponseEntity.ok()
            .contentType(MediaType.TEXT_PLAIN)
            // ruleid: tainted-html-string
            .body(payload);;

        } else {
            return new ResponseEntity<>(HttpStatus.BAD_REQUEST);
        }
    }
}
