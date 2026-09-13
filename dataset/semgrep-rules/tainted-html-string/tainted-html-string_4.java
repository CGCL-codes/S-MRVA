
package org.sasanlabs.service.vulnerability.xss.reflected;

import org.apache.commons.text.StringEscapeUtils;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestParam;

@VulnerableAppRestController(descriptionLabel = "XSS_VULNERABILITY", value = "XSSInImgTagAttribute")
public class XSSInImgTagAttribute {

    @VulnerableAppRequestMapping(value = LevelConstants.LEVEL_5, htmlTemplate = "LEVEL_1/XSS")
    public ResponseEntity<String> getVulnerablePayloadLevel5(
            @RequestParam(PARAMETER_NAME) String imageLocation) {

        String vulnerablePayloadWithPlaceHolder = "<img src=%s width=\"400\" height=\"300\"/>";
        StringBuilder payload = new StringBuilder();

        String validatedFileName = imageLocation;

        if (imageLocation.contains(Constants.NULL_BYTE_CHARACTER)) {
            validatedFileName =
                    imageLocation.substring(
                            0, imageLocation.indexOf(Constants.NULL_BYTE_CHARACTER));
        }

        if (allowedValues.contains(validatedFileName)) {
            payload.append(
                    String.format(
                            vulnerablePayloadWithPlaceHolder,
                            StringEscapeUtils.escapeHtml4(imageLocation)));
        }

        // ruleid: tainted-html-string
        return new ResponseEntity<>(payload.toString(), HttpStatus.OK);
    }
}
